# -*- coding: utf-8 -*-
"""
    IMDB Trailers Kodi Addon
    Copyright (C) 2018 gujal

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

# Imports
import re
import sys
import datetime
import json
from kodi_six import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs
from bs4 import BeautifulSoup, SoupStrainer
from resources.lib import client
import six
from six.moves import urllib_parse
try:
    import StorageServer
except:
    import storageserverdummy as StorageServer

# HTMLParser() deprecated in Python 3.4 and removed in Python 3.9
if sys.version_info >= (3, 4, 0):
    import html
    _html_parser = html
else:
    from six.moves import html_parser
    _html_parser = html_parser.HTMLParser()

_addon = xbmcaddon.Addon()
_addonID = _addon.getAddonInfo('id')
_plugin = _addon.getAddonInfo('name')
_version = _addon.getAddonInfo('version')
_icon = _addon.getAddonInfo('icon')
_fanart = _addon.getAddonInfo('fanart')
_language = _addon.getLocalizedString
_settings = _addon.getSetting
_addonpath = 'special://profile/addon_data/{}/'.format(_addonID)
# DEBUG
DEBUG = _settings("DebugMode") == "true"
# View Mode
force_mode = _settings("forceViewMode") == "true"
if force_mode:
    menu_mode = int(_settings('MenuMode'))
    view_mode = int(_settings('VideoMode'))

if not xbmcvfs.exists(_addonpath):
    xbmcvfs.mkdir(_addonpath)

cache = StorageServer.StorageServer(_plugin if six.PY3 else _plugin.encode('utf8'), _settings('timeout'))
CONTENT_URL = 'https://www.imdb.com/trailers/'
SHOWING_URL = 'https://www.imdb.com/showtimes/location/'
COMING_URL = 'https://www.imdb.com/movies-coming-soon/{}-{:02}'  # https://www.imdb.com/calendar/
ID_URL = 'https://www.imdb.com/_json/video/{0}'
SHOWING_TRAILER = 'https://www.imdb.com/showtimes/title/{0}/'
DETAILS_PAGE = "https://www.imdb.com/video/{0}/"
quality = int(_settings("video_quality")[:-1])
LOGINFO = xbmc.LOGINFO if six.PY3 else xbmc.LOGNOTICE

if not xbmcvfs.exists(_addonpath + 'settings.xml'):
    _addon.openSettings()


class Main(object):
    def __init__(self):
        action = self.parameters('action')
        if action == 'list3':
            self.list_contents3()
        elif action == 'list2':
            self.list_contents2()
        elif action == 'list1':
            self.list_showing()
        elif action == 'play_id':
            self.play_id()
        elif action == 'play':
            self.play()
        elif action == 'play_showing':
            self.play_showing()
        elif action == 'search':
            self.search()
        elif action == 'search_word':
            self.search_word()
        elif action == 'clear':
            self.clear_cache()
        else:
            self.main_menu()

    def main_menu(self):
        if DEBUG:
            self.log('main_menu()')
        category = [{'title': _language(30201), 'key': 'showing'},
                    {'title': _language(30202), 'key': 'coming'},
                    {'title': _language(30208), 'key': 'trending'},
                    {'title': _language(30209), 'key': 'anticipated'},
                    {'title': _language(30210), 'key': 'popular'},
                    {'title': _language(30211), 'key': 'recent'},
                    {'title': _language(30206), 'key': 'search'},
                    {'title': _language(30207), 'key': 'cache'}]
        for i in category:
            listitem = xbmcgui.ListItem(i['title'])
            listitem.setArt({'thumb': _icon,
                             'fanart': _fanart,
                             'icon': _icon})

            if i['key'] == 'cache':
                url = sys.argv[0] + '?' + urllib_parse.urlencode({'action': 'clear'})
            elif i['key'] == 'search':
                url = sys.argv[0] + '?' + urllib_parse.urlencode({'action': 'search'})
            elif i['key'] == 'showing':
                url = sys.argv[0] + '?' + urllib_parse.urlencode({'action': 'list1',
                                                                  'key': i['key']})
            elif i['key'] == 'coming':
                url = sys.argv[0] + '?' + urllib_parse.urlencode({'action': 'list2',
                                                                  'key': i['key']})
            else:
                url = sys.argv[0] + '?' + urllib_parse.urlencode({'action': 'list3',
                                                                  'key': i['key']})

            xbmcplugin.addDirectoryItems(int(sys.argv[1]), [(url, listitem, True)])

        # Sort methods and content type...
        xbmcplugin.addSortMethod(handle=int(sys.argv[1]), sortMethod=xbmcplugin.SORT_METHOD_NONE)
        xbmcplugin.setContent(int(sys.argv[1]), 'addons')
        if force_mode:
            xbmc.executebuiltin('Container.SetViewMode({})'.format(menu_mode))
        # End of directory...
        xbmcplugin.endOfDirectory(int(sys.argv[1]), True)

    def clear_cache(self):
        """
        Clear the cache database.
        """
        if DEBUG:
            self.log('clear_cache()')
        msg = 'Cached Data has been cleared'
        cache.table_name = _plugin
        cache.cacheDelete(r'%fetch%')
        xbmcgui.Dialog().notification(_plugin, msg, _icon, 3000, False)

    def search(self):
        if DEBUG:
            self.log('search()')
        keyboard = xbmc.Keyboard()
        keyboard.setHeading('Search IMDb by Title')
        keyboard.doModal()
        if keyboard.isConfirmed():
            search_text = urllib_parse.quote(keyboard.getText())
        else:
            search_text = ''
        xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=False)
        if len(search_text) > 2:
            url = sys.argv[0] + '?' + urllib_parse.urlencode({'action': 'search_word',
                                                              'keyword': search_text})
            xbmc.executebuiltin("Container.Update({0})".format(url))
        else:
            msg = 'Need atleast 3 characters'
            xbmcgui.Dialog().notification(_plugin, msg, _icon, 3000, False)
            xbmc.executebuiltin("Container.Update({0},replace)".format(sys.argv[0]))

    def search_word(self):
        search_text = self.parameters('keyword')
        if DEBUG:
            self.log('search_word("{0}")'.format(search_text))
        url = 'https://www.imdb.com/find?q={}&s=tt'.format(search_text)
        page_data = cache.cacheFunction(fetch, url)
        tlink = SoupStrainer('table', {'class': 'findList'})
        soup = BeautifulSoup(page_data, "html.parser", parse_only=tlink)
        items = soup.find_all('tr')
        for item in items:
            imdb_id = item.find('a').get('href').split('/')[2]
            title = item.text.strip()
            icon = item.find('img')['src']
            poster = icon.split('_')[0] + 'jpg'
            listitem = xbmcgui.ListItem(title)
            listitem.setArt({'thumb': poster,
                             'icon': icon,
                             'poster': poster,
                             'fanart': _fanart})

            listitem.setInfo(type='video',
                             infoLabels={'title': title})

            listitem.setProperty('IsPlayable', 'true')
            url = sys.argv[0] + '?' + urllib_parse.urlencode({'action': 'play_id',
                                                              'imdb': imdb_id})
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, listitem, False)

        # Sort methods and content type...
        xbmcplugin.setContent(int(sys.argv[1]), 'movies')
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
        if force_mode:
            xbmc.executebuiltin('Container.SetViewMode({})'.format(view_mode))
        # End of directory...
        xbmcplugin.endOfDirectory(int(sys.argv[1]), updateListing=True, cacheToDisc=False)

    def list_showing(self):
        if DEBUG:
            self.log('list_showing()')

        page_data = cache.cacheFunction(fetch, SHOWING_URL)
        tlink = SoupStrainer('div', {'class': 'lister-list'})
        mdiv = BeautifulSoup(page_data, "html.parser", parse_only=tlink)
        videos = mdiv.find_all('div', {'class': 'lister-item'})
        h = _html_parser

        for video in videos:
            imdbId = video.find('div', {'class': 'lister-item-image'}).get('data-tconst')
            title = video.find('div', {'class': 'title'}).text
            plot = video.find('p', {'class': ''}).text
            if six.PY2:
                title = title.encode('utf-8')
                plot = plot.encode('utf-8')
            icon = video.find('img').get('loadlate')
            poster = icon.split('_')[0] + 'jpg'
            genre = video.find('span', {'class': 'genre'})
            genre = genre.text.strip().split(', ') if genre else ''
            rdate = video.find('span', {'name': 'release_date'}).get('data-value')
            rating = video.find('span', {'name': 'user_rating'}).get('data-value')
            mpaa = video.find('span', {'class': 'certificate'})
            mpaa = mpaa.text.strip() if mpaa else ''
            year = int(rdate[0:4])
            premiered = rdate[0:4] + '-' + rdate[4:6] + '-' + rdate[6:]
            items = video.find_all('p', {'class': 'text-muted'})
            cast = []
            director = []
            for item in items:
                ms = item.find_all('a')
                for m in ms:
                    if 'li_dr_' in m.get('href'):
                        director.append(m.text.strip().encode('utf-8') if six.PY2 else m.text.strip())
                    else:
                        cast.append(m.text.strip().encode('utf-8') if six.PY2 else m.text.strip())

            labels = {'title': h.unescape(title),
                      'plot': h.unescape(plot),
                      'director': director,
                      'cast': cast,
                      'year': year,
                      'rating': float(rating),
                      'premiered': premiered,
                      'genre': genre,
                      'mpaa': mpaa,
                      'mediatype': 'movie'}

            listitem = xbmcgui.ListItem(title)
            listitem.setArt({'thumb': poster,
                             'icon': icon,
                             'poster': poster,
                             'fanart': _fanart})

            listitem.setInfo(type='video', infoLabels=labels)

            listitem.setProperty('IsPlayable', 'true')
            url = sys.argv[0] + '?' + urllib_parse.urlencode({'action': 'play_showing',
                                                              'imdb': imdbId})
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, listitem, False)

        # Sort methods and content type...
        xbmcplugin.setContent(int(sys.argv[1]), 'movies')
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
        if force_mode:
            xbmc.executebuiltin('Container.SetViewMode({})'.format(view_mode))
        # End of directory...
        xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)

    def list_contents2(self):
        key = self.parameters('key')
        if DEBUG:
            self.log('content_list2("{0}")'.format(key))

        year, month, _ = datetime.date.today().isoformat().split('-')
        page_data = ''
        nyear = int(year)
        for i in range(4):
            nmonth = int(month) + i
            if nmonth > 12:
                nmonth = nmonth - 12
                nyear = int(year) + 1
            url = COMING_URL.format(nyear, nmonth)
            page_data += cache.cacheFunction(fetch, url)
        tlink = SoupStrainer('div', {'class': 'list detail'})

        mdiv = BeautifulSoup(page_data, "html.parser", parse_only=tlink)
        videos = mdiv.find_all('div', {'class': 'lister-item'})
        h = _html_parser

        for video in videos:
            imdbId = video.find('div', {'class': 'lister-item-image'}).get('data-tconst')
            title = video.find('div', {'class': 'title'}).text
            plot = video.find('p', {'class': ''}).text
            icon = video.find('img').get('loadlate')
            poster = icon.split('_')[0] + 'jpg'
            genre = video.find('span', {'class': 'genre'})
            genre = genre.text.strip().split(', ') if genre else ''
            rdate = video.find('span', {'name': 'release_date'}).get('data-value')
            rating = video.find('span', {'name': 'user_rating'}).get('data-value')
            mpaa = video.find('span', {'class': 'certificate'})
            mpaa = mpaa.text.strip() if mpaa else ''
            year = int(rdate[0:4])
            premiered = rdate[0:4] + '-' + rdate[4:6] + '-' + rdate[6:]
            items = video.find_all('p', {'class': 'text-muted'})
            cast = []
            director = []
            for item in items:
                ms = item.find_all('a')
                for m in ms:
                    if 'li_dr_' in m.get('href'):
                        director.append(m.text)
                    else:
                        cast.append(m.text.strip())

            labels = {'title': h.unescape(title),
                      'plot': h.unescape(plot),
                      'director': director,
                      'cast': cast,
                      'year': year,
                      'rating': float(rating),
                      'premiered': premiered,
                      'genre': genre,
                      'mpaa': mpaa,
                      'mediatype': 'movie'}

            listitem = xbmcgui.ListItem(title)
            listitem.setArt({'thumb': poster,
                             'icon': icon,
                             'poster': poster,
                             'fanart': _fanart})

            listitem.setInfo(type='video', infoLabels=labels)

            listitem.setProperty('IsPlayable', 'true')
            url = sys.argv[0] + '?' + urllib_parse.urlencode({'action': 'play_showing',
                                                              'imdb': imdbId})
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, listitem, False)

        # Sort methods and content type...
        xbmcplugin.setContent(int(sys.argv[1]), 'movies')
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
        if force_mode:
            xbmc.executebuiltin('Container.SetViewMode({})'.format(view_mode))
        # End of directory...
        xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)

    def list_contents3(self):
        key = self.parameters('key')
        if DEBUG:
            self.log('content_list3("{0}")'.format(key))

        videos = cache.cacheFunction(fetchdata3, key)
        for video in videos:
            if DEBUG:
                self.log(repr(video))
            if key == 'trending' or key == 'anticipated' or key == 'popular':
                title = video.get('titleText').get('text')
                videoId = video.get('latestTrailer').get('id')
                duration = video.get('latestTrailer').get('runtime').get('value')
                name = video.get('latestTrailer').get('name').get('value')
                try:
                    plot = video.get('latestTrailer').get('description').get('value')
                except AttributeError:
                    plot = ''
                if plot == name or len(plot) == 0:
                    try:
                        plot = video.get('plot').get('plotText').get('plainText')
                    except AttributeError:
                        pass
                try:
                    fanart = video.get('latestTrailer').get('thumbnail').get('url', '')
                except AttributeError:
                    fanart = ''
                try:
                    poster = video.get('primaryImage').get('url', '')
                except AttributeError:
                    poster = fanart
                try:
                    year = video.get('releaseDate').get('year')
                except AttributeError:
                    year = ''
            elif key == 'recent':
                try:
                    title = video.get('primaryTitle', {}).get('titleText', {}).get('text', '')
                except AttributeError:
                    title = ''
                videoId = video.get('id')
                duration = video.get('runtime').get('value')
                name = video.get('name').get('value')
                try:
                    plot = video.get('description', {}).get('value', '')
                except AttributeError:
                    plot = ''
                if plot == name or len(plot) == 0:
                    try:
                        plot = video.get('primaryTitle', {}).get('plot', {}).get('plotText', {}).get('plainText', '')
                    except AttributeError:
                        pass
                try:
                    fanart = video.get('thumbnail', {}).get('url', '')
                except AttributeError:
                    fanart = ''
                try:
                    poster = video.get('primaryTitle').get('primaryImage').get('url', '')
                except AttributeError:
                    poster = fanart
                try:
                    year = video.get('primaryTitle', {}).get('releaseDate').get('year', '')
                except AttributeError:
                    year = ''

            if title in name:
                name = name.replace(title, '').strip()
            if len(name) > 0:
                if six.PY2:
                    name = name.encode('utf8')
                    title = title.encode('utf8')
                title = '{0} [COLOR cyan][I]{1}[/I][/COLOR]'.format(title, name)
            labels = {'title': title,
                      'plot': plot,
                      'duration': duration,
                      'mediatype': 'movie'}
            if year:
                labels.update({'year': year})

            listitem = xbmcgui.ListItem(title)
            listitem.setArt({'thumb': poster,
                             'icon': poster,
                             'poster': poster,
                             'fanart': fanart})

            listitem.setInfo(type='video', infoLabels=labels)

            listitem.setProperty('IsPlayable', 'true')
            url = sys.argv[0] + '?' + urllib_parse.urlencode({'action': 'play',
                                                              'videoid': videoId})
            xbmcplugin.addDirectoryItem(int(sys.argv[1]), url, listitem, False)

        # Sort methods and content type...
        xbmcplugin.setContent(int(sys.argv[1]), 'movies')
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_UNSORTED)
        xbmcplugin.addSortMethod(int(sys.argv[1]), xbmcplugin.SORT_METHOD_VIDEO_TITLE)
        if force_mode:
            xbmc.executebuiltin('Container.SetViewMode({})'.format(view_mode))
        # End of directory...
        xbmcplugin.endOfDirectory(int(sys.argv[1]), cacheToDisc=True)

    def fetch_video_url(self, video_id):
        if DEBUG:
            self.log('fetch_video_url("{0})'.format(video_id))
        vidurl = DETAILS_PAGE.format(video_id)
        pagedata = cache.cacheFunction(fetch, vidurl)
        r = re.search(r'application/json">([^<]+)', pagedata)
        if r:
            details = json.loads(r.group(1)).get('props', {}).get('pageProps', {}).get('videoPlaybackData', {}).get('video')
            if details:
                details = {i.get('displayName').get('value'): i.get('url') for i in details.get('playbackURLs') if i.get('mimeType') == 'video/mp4'}
                vids = [(x[:-1], details[x]) for x in details.keys() if 'p' in x]
                vids.sort(key=lambda x: int(x[0]), reverse=True)
                if DEBUG:
                    self.log('Found %s videos' % len(vids))
                for qual, vid in vids:
                    if int(qual) <= quality:
                        if DEBUG:
                            self.log('videoURL: %s' % vid)
                        return vid

        return None

    def play(self):
        if DEBUG:
            self.log('play()')
        title = xbmc.getInfoLabel("ListItem.Title")
        thumbnail = xbmc.getInfoImage("ListItem.Thumb")
        plot = xbmc.getInfoLabel("ListItem.Plot")
        # only need to add label, icon and thumbnail, setInfo() and addSortMethod() takes care of label2
        listitem = xbmcgui.ListItem(title)
        listitem.setArt({'thumb': thumbnail})

        # set the key information
        listitem.setInfo('video', {'title': title,
                                   'plot': plot,
                                   'plotOutline': plot})

        listitem.setPath(cache.cacheFunction(self.fetch_video_url, self.parameters('videoid')))
        xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem=listitem)

    def play_showing(self):
        imdb_id = self.parameters('imdb')
        if DEBUG:
            self.log('play_showing()')

        iurl = SHOWING_TRAILER.format(imdb_id)
        page_data = cache.cacheFunction(fetch, iurl)
        r = re.search(r'data-video="(.*?)"\s*itemprop="trailer"', page_data)
        if r:
            title = xbmc.getInfoLabel("ListItem.Title")
            thumbnail = xbmc.getInfoImage("ListItem.Thumb")
            plot = xbmc.getInfoLabel("ListItem.Plot")
            # only need to add label, icon and thumbnail, setInfo() and addSortMethod() takes care of label2
            listitem = xbmcgui.ListItem(title)
            listitem.setArt({'thumb': thumbnail})

            # set the key information
            listitem.setInfo('video', {'title': title,
                                       'plot': plot,
                                       'plotOutline': plot})

            listitem.setPath(cache.cacheFunction(self.fetch_video_url, r.group(1)))
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem=listitem)
        else:
            msg = 'No Trailers available'
            xbmcgui.Dialog().notification(_plugin, msg, _icon, 3000, False)

    def play_id(self):
        imdb_id = self.parameters('imdb')
        if DEBUG:
            self.log('play_id("{0})'.format(imdb_id))

        iurl = ID_URL.format(imdb_id)
        details = cache.cacheFunction(fetch, iurl)
        if not isinstance(details, dict):
            details = {}
        video_list = details.get('playlists', {}).get(imdb_id, {}).get('listItems')
        if video_list:
            videoid = video_list[0]['videoId']
            if DEBUG:
                self.log('VideoID: {0}'.format(videoid))
            title = xbmc.getInfoLabel("ListItem.Title")
            thumbnail = xbmc.getInfoImage("ListItem.Thumb")
            listitem = xbmcgui.ListItem(title)
            listitem.setArt({'thumb': thumbnail})
            # set the key information
            listitem.setInfo('video', {'title': title})

            encodings = details['videoMetadata'][videoid]['encodings']
            vids = []
            for item in encodings:
                if item['mimeType'] == 'video/mp4':
                    qual = "360p" if item["definition"] == "SD" else item["definition"]
                    vids.append((qual[:-1], item["videoUrl"]))
            vids.sort(key=lambda elem: int(elem[0]), reverse=True)
            for qual, vid in vids:
                if int(qual) <= quality:
                    if DEBUG:
                        self.log('videoURL: %s' % vid)
                    videoUrl = vid
                    break

            listitem.setPath(videoUrl)
            xbmcplugin.setResolvedUrl(int(sys.argv[1]), True, listitem=listitem)
        else:
            msg = 'No Trailers available'
            xbmcgui.Dialog().notification(_plugin, msg, _icon, 3000, False)

    def parameters(self, arg):
        _parameters = urllib_parse.parse_qs(urllib_parse.urlparse(sys.argv[2]).query)
        val = _parameters.get(arg, '')
        if isinstance(val, list):
            val = val[0]
        return val

    def log(self, description):
        xbmc.log("[ADD-ON] '{} v{}': {}".format(_plugin, _version, description), LOGINFO)


def fetch(url):
    headers = {'Referer': 'https://www.imdb.com/',
               'Origin': 'https://www.imdb.com'}
    if 'graphql' in url:
        headers.update({'content-type': 'application/json'})
    r = client.request(url, headers=headers)
    return r


def fetchdata3(key):
    api_url = 'https://graphql.prod.api.imdb.a2z.com/'
    vpar = {'limit': 100}
    if key == 'trending':
        query_pt1 = ("query TrendingTitles($limit: Int!, $paginationToken: String) {"
                     "  trendingTitles(limit: $limit, paginationToken: $paginationToken) {"
                     "    titles {"
                     "      latestTrailer {"
                     "        ...TrailerVideoMeta"
                     "      }"
                     "      ...TrailerTitleMeta"
                     "    }"
                     "    paginationToken"
                     "  }"
                     "}")
        ptoken = "60"
        opname = "TrendingTitles"
    elif key == 'recent':
        query_pt1 = ("query RecentVideos($limit: Int!, $paginationToken: String, $queryFilter: RecentVideosQueryFilter!) {"
                     "  recentVideos(limit: $limit, paginationToken: $paginationToken, queryFilter: $queryFilter) {"
                     "    videos {"
                     "      ...TrailerVideoMeta"
                     "      primaryTitle {"
                     "        ...TrailerTitleMeta"
                     "      }"
                     "    }"
                     "    paginationToken"
                     "  }"
                     "}")
        ptoken = "blank"
        opname = "RecentVideos"
        vpar.update({'queryFilter': {"contentTypes": ["TRAILER"]}})
    elif key == 'anticipated' or key == 'popular':
        query_pt1 = ("query PopularTitles($limit: Int!, $paginationToken: String, $queryFilter: PopularTitlesQueryFilter!) {"
                     "  popularTitles(limit: $limit, paginationToken: $paginationToken, queryFilter: $queryFilter) {"
                     "    titles {"
                     "      latestTrailer {"
                     "        ...TrailerVideoMeta"
                     "      }"
                     "      ...TrailerTitleMeta"
                     "    }"
                     "    paginationToken"
                     "  }"
                     "}")
        ptoken = "blank"
        opname = "PopularTitles"
        d1 = datetime.date.today().isoformat()
        if key == 'anticipated':
            vpar.update({'queryFilter': {"releaseDateRange": {"start": d1}}})
        else:
            vpar.update({'queryFilter': {"releaseDateRange": {"end": d1}}})

    query_pt2 = ("fragment TrailerTitleMeta on Title {"
                 "  id"
                 "  titleText {"
                 "    text"
                 "  }"
                 "  plot {"
                 "    plotText {"
                 "      plainText"
                 "    }"
                 "  }"
                 "  primaryImage {"
                 "    url"
                 "  }"
                 "  releaseDate {"
                 "    year"
                 "  }"
                 "}"
                 "fragment TrailerVideoMeta on Video {"
                 "  id"
                 "  name {"
                 "    value"
                 "  }"
                 "  runtime {"
                 "    value"
                 "  }"
                 "  description {"
                 "    value"
                 "  }"
                 "  thumbnail {"
                 "    url"
                 "  }"
                 "}")

    qstr = urllib_parse.quote(query_pt1 + query_pt2, "(")
    items = []
    pages = 0

    while len(items) < 200 and ptoken and pages < 5:
        if ptoken != "blank":
            vpar.update({"paginationToken": ptoken})

        vtxt = urllib_parse.quote(json.dumps(vpar).replace(" ", ""))
        data = cache.cacheFunction(fetch, "{0}?operationName={1}&query={2}&variables={3}".format(api_url, opname, qstr, vtxt))
        pages += 1
        data = data.get('data')

        if key == 'trending' or key == 'anticipated' or key == 'popular':
            if key == 'trending':
                data = data.get('trendingTitles')
            elif key == 'anticipated' or key == 'popular':
                data = data.get('popularTitles')
            titles = data.get('titles')
            for title in titles:
                if title.get('latestTrailer'):
                    items.append(title)
        elif key == 'recent':
            data = data.get('recentVideos')
            titles = data.get('videos')
            items.extend(titles)

        if len(titles) < 1:
            ptoken = None
        else:
            ptoken = data.get('paginationToken')

    return items
