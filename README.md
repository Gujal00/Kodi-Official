# Kodi-Official

Source for addons in Kodi Repository

## plugin.video.dailymotion_com

### Kodi Addon for playing videos from Dailymotion website

![License](https://img.shields.io/badge/license-GPL--3.0--only-success.svg)
![Kodi Version](https://img.shields.io/badge/kodi-jarvis%2B-success.svg)
![Contributors](https://img.shields.io/github/contributors/Gujal00/Kodi-Official.svg)

Head to the [Forum for support](https://forum.kodi.tv/showthread.php?tid=142626)

DailyMotion streams can be integrated into the video library with strm files.

The syntax for a DailyMotion-URL for video such as
`http://www.dailymotion.com/video/%VIDEOID%_DESCRIPTIONTEXT` is
> plugin://plugin.video.dailymotion_com/?url=%VIDEOID%&mode=playVideo

and for Live Streams the usage is as follows
> plugin://plugin.video.dailymotion_com/?url=%VIDEOID%&mode=playLiveVideo

## plugin.video.imdb.trailers

### Kodi Addon for playing trailers from IMDb website

![License](https://img.shields.io/badge/license-GPL--3.0--only-success.svg)
![Kodi Version](https://img.shields.io/badge/kodi-leia%2B-success.svg)
![Contributors](https://img.shields.io/github/contributors/Gujal00/Kodi-Official.svg)

Head to the [Forum for support](https://forum.kodi.tv/showthread.php?tid=352127)

You can also call this addon from other addons or in STRM files as below.
> plugin://plugin.video.imdb.trailers/?action=play_id&imdb=imdb_id

For example,

> plugin://plugin.video.imdb.trailers/?action=play_id&imdb=tt0113957
