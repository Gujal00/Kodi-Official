"""
    iTunes Movie Trailers Kodi Addon
    Copyright (C) 2014 tknorris
    Copyright (C) 2022 gujal

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import json
from six.moves import urllib_parse, urllib_request, urllib_error
import socket
import ssl
import time
from lib import kodi, log_utils, utils, cache

logger = log_utils.Logger.get_logger()


def __enum(**enums):
    return type('Enum', (), enums)


TEMP_ERRORS = [500, 502, 503, 504, 520, 521, 522, 524]
SECTIONS = __enum(TV='TV', MOVIES='Movies')
TRAKT_SECTIONS = {SECTIONS.TV: 'shows', SECTIONS.MOVIES: 'movies'}


class TraktError(Exception):
    pass


class TraktAuthError(Exception):
    pass


class TraktNotFoundError(Exception):
    pass


class TransientTraktError(Exception):
    pass


BASE_URL = 'api-v2launch.trakt.tv'
V2_API_KEY = '587669004d4fe02bcde9b1ff4a5db964574c2db2afadd8fdf0e0690ef0155fc8'
CLIENT_SECRET = '09e94c82e96fe2f322cc4436d6d048f84ecb1feda58efb003372c4a86599980e'
REDIRECT_URI = 'urn:ietf:wg:oauth:2.0:oob'
HIDDEN_SIZE = 100
RESULTS_LIMIT = 10


class Trakt_API():
    def __init__(self, token=None, use_https=False, list_size=RESULTS_LIMIT, timeout=5):
        self.token = token
        self.protocol = 'https://' if use_https else 'http://'
        self.timeout = None if timeout == 0 else timeout
        self.list_size = list_size

    def get_code(self):
        url = '/oauth/device/code'
        data = {'client_id': V2_API_KEY}
        return self.__call_trakt(url, data=data, auth=False, cached=False)

    def get_device_token(self, code):
        url = '/oauth/device/token'
        data = {'client_id': V2_API_KEY, 'client_secret': CLIENT_SECRET, 'code': code}
        return self.__call_trakt(url, data=data, auth=False, cached=False)

    def refresh_token(self, refresh_token):
        url = '/oauth/token'
        data = {'client_id': V2_API_KEY, 'client_secret': CLIENT_SECRET, 'redirect_uri': REDIRECT_URI}
        if refresh_token:
            data['refresh_token'] = refresh_token
            data['grant_type'] = 'refresh_token'
        else:
            raise TraktError('Can not refresh trakt token. Trakt reauthorizion required.')

        return self.__call_trakt(url, data=data, auth=False, cached=False)

    def show_list(self, slug, section, username=None, auth=True, cached=True):
        if not username:
            username = 'me'
            cache_limit = self.__get_cache_limit('lists', 'updated_at', cached)
        else:
            cache_limit = 1  # cache other user's list for one hour

        url = '/users/%s/lists/%s/items' % (utils.to_slug(username), slug)
        # params = {'extended': 'full,images'}
        params = None
        list_data = self.__call_trakt(url, params=params, auth=auth, cache_limit=cache_limit, cached=cached)
        return [item[item['type']] for item in list_data if item['type'] == TRAKT_SECTIONS[section][:-1]]

    def show_watchlist(self, section):
        url = '/users/me/watchlist/%s' % (TRAKT_SECTIONS[section])
        params = {'extended': 'full,images'}
        cache_limit = self.__get_cache_limit('lists', 'updated_at', cached=True)
        response = self.__call_trakt(url, params=params, cache_limit=cache_limit)
        return [item[TRAKT_SECTIONS[section][:-1]] for item in response]

    def get_list_header(self, slug, username=None, auth=True):
        if not username:
            username = 'me'
        url = '/users/%s/lists/%s' % (utils.to_slug(username), slug)
        return self.__call_trakt(url, auth=auth)

    def get_lists(self, username=None):
        if not username:
            username = 'me'
            cache_limit = self.__get_cache_limit('lists', 'updated_at', True)
        else:
            cache_limit = 0
        url = '/users/%s/lists' % (utils.to_slug(username))
        return self.__call_trakt(url, cache_limit=cache_limit)

    def add_to_list(self, section, slug, items):
        return self.__manage_list('add', section, slug, items)

    def remove_from_list(self, section, slug, items):
        return self.__manage_list('remove', section, slug, items)

    def add_to_watchlist(self, section, items):
        return self.__manage_watchlist('add', section, items)

    def remove_from_watchlist(self, section, items):
        return self.__manage_watchlist('remove', section, items)

    def get_user_profile(self, username=None, cached=True):
        if username is None:
            username = 'me'
        url = '/users/%s' % (utils.to_slug(username))
        return self.__call_trakt(url, cached=cached)

    def get_last_activity(self, media=None, activity=None):
        url = '/sync/last_activities'
        result = self.__call_trakt(url, cache_limit=.01)
        if media is not None and media in result:
            if activity is not None and activity in result[media]:
                return result[media][activity]
            else:
                return result[media]
        return result

    def search(self, section, query, page=None):
        url = '/search'
        params = {'type': TRAKT_SECTIONS[section][:-1], 'query': query, 'limit': self.list_size}
        if page:
            params['page'] = page
        response = self.__call_trakt(url, params=params)
        return [item[TRAKT_SECTIONS[section][:-1]] for item in response]

    def __get_cache_limit(self, media, activity, cached):
        if cached:
            activity = self.get_last_activity(media, activity)
            cache_limit = (time.time() - utils.iso_2_utc(activity))
            logger.log('Now: %s Last: %s Last TS: %s Cache Limit: %.2fs (%.2fh)' % (time.time(), utils.iso_2_utc(activity), activity, cache_limit, cache_limit / 60 / 60), log_utils.LOGDEBUG)
            cache_limit = cache_limit / 60 / 60
        else:
            cache_limit = 0
        return cache_limit

    def __manage_list(self, action, section, slug, items):
        url = '/users/me/lists/%s/items' % (slug)
        if action == 'remove':
            url = url + '/remove'
        if not isinstance(items, (list, tuple)):
            items = [items]
        data = self.__make_media_list_from_list(section, items)
        return self.__call_trakt(url, data=data, cache_limit=0)

    def __manage_watchlist(self, action, section, items):
        url = '/sync/watchlist'
        if action == 'remove':
            url = url + '/remove'
        if not isinstance(items, (list, tuple)):
            items = [items]
        data = self.__make_media_list_from_list(section, items)
        return self.__call_trakt(url, data=data, cache_limit=0)

    def __make_media_list_from_list(self, section, items):
        data = {TRAKT_SECTIONS[section]: []}
        for item in items:
            ids = {'ids': item}
            data[TRAKT_SECTIONS[section]].append(ids)
        return data

    def __call_trakt(self, url, method=None, data=None, params=None, auth=True, cache_limit=.25, cached=True):
        if not cached:
            cache_limit = 0
        json_data = json.dumps(data) if data else None
        headers = {'Content-Type': 'application/json', 'trakt-api-key': V2_API_KEY, 'trakt-api-version': 2}
        url = '%s%s%s' % (self.protocol, BASE_URL, url)
        if params:
            url = url + '?' + urllib_parse.urlencode(params)

        args = [url]
        kwargs = {'method': method, 'data': data, 'params': params, 'auth': auth}
        func_name = '__call_trakt'
        cached, cached_result = cache._get_func(func_name, args=args, kwargs=kwargs, cache_limit=cache_limit)
        if cached:
            result = cached_result
            logger.log('***Using cached result for: %s' % (url), log_utils.LOGDEBUG)
        else:
            auth_retry = False
            while True:
                try:
                    if auth:
                        headers.update({'Authorization': 'Bearer %s' % (self.token)})
                    logger.log('***Trakt Call: %s, header: %s, data: %s cache_limit: %s cached: %s' % (url, headers, json_data, cache_limit, cached), log_utils.LOGDEBUG)
                    request = urllib_request.Request(url, data=json_data, headers=headers)
                    if method is not None:
                        request.get_method = lambda: method.upper()
                    response = urllib_request.urlopen(request, timeout=self.timeout)
                    result = ''
                    while True:
                        data = response.read()
                        if not data:
                            break
                        result += data
                    cache._save_func(func_name, args=args, kwargs=kwargs, result=result)
                    break
                except (ssl.SSLError, socket.timeout) as e:
                    if cached_result:
                        result = cached_result
                        logger.log('Temporary Trakt Error (%s). Using Cached Page Instead.' % (str(e)), log_utils.LOGWARNING)
                    else:
                        raise TransientTraktError('Temporary Trakt Error: ' + str(e))
                except urllib_error.URLError as e:
                    if isinstance(e, urllib_error.HTTPError):
                        if e.code in TEMP_ERRORS:
                            if cached_result:
                                result = cached_result
                                logger.log('Temporary Trakt Error (%s). Using Cached Page Instead.' % (str(e)), log_utils.LOGWARNING)
                                break
                            else:
                                raise TransientTraktError('Temporary Trakt Error: ' + str(e))
                        elif e.code == 401 or e.code == 405:
                            # token is fine, profile is private
                            if e.info().getheader('X-Private-User') == 'true':
                                raise TraktAuthError('Object is No Longer Available (%s)' % (e.code))
                            # auth failure retry or a token request
                            elif auth_retry or url.endswith('/oauth/token'):
                                self.token = None
                                kodi.set_setting('trakt_oauth_token', '')
                                kodi.set_setting('trakt_refresh_token', '')
                                raise TraktAuthError('Trakt Call Authentication Failed (%s)' % (e.code))
                            # first try token fail, try to refresh token
                            else:
                                result = self.refresh_token(kodi.get_setting('trakt_refresh_token'))
                                self.token = result['access_token']
                                kodi.set_setting('trakt_oauth_token', result['access_token'])
                                kodi.set_setting('trakt_refresh_token', result['refresh_token'])
                                auth_retry = True
                        elif e.code == 404:
                            raise TraktNotFoundError('Object Not Found (%s)' % (e.code))
                        else:
                            raise
                    elif isinstance(e.reason, socket.timeout) or isinstance(e.reason, ssl.SSLError):
                        if cached_result:
                            result = cached_result
                            logger.log('Temporary Trakt Error (%s). Using Cached Page Instead' % (str(e)), log_utils.LOGWARNING)
                            break
                        else:
                            raise TransientTraktError('Temporary Trakt Error: ' + str(e))
                    else:
                        raise TraktError('Trakt Error: ' + str(e))
                except:
                    raise

        try:
            js_data = utils.json_loads_as_str(result)
        except ValueError:
            js_data = ''
            if result:
                logger.log('Invalid JSON Trakt API Response: %s - |%s|' % (url, js_data), log_utils.LOGERROR)

        # logger.log('Trakt Response: %s' % (response), xbmc.LOGDEBUG)
        return js_data
