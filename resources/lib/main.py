import typing as t

from kodi_useful import (
    router,
    Addon,
    Directory,
)
from kodi_useful.enums import Content, Scope
import xbmcgui
import xbmcplugin
from YDWrapper import extract_source

from . import pages


addon = Addon(
    locale_map_file='resources/language/locale_map.json',
)


@router.route
def play_video(page_url: t.Annotated[str, Scope.QUERY]):
    """Воспроизводит видео файл."""
    # item = xbmcgui.ListItem('Test', offscreen=True)
    # item.setPath(page_url)
    # item.setProperty('inputstream.adaptive.stream_selection_type', 'adaptive')
    # item.setProperty('inputstream.adaptive.chooser_resolution_max', 'auto')
    # item.setProperty('inputstream', 'inputstream.adaptive')
    # item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    # item.setMimeType('application/dash+xml')
    # # item.setProperty("IsPlayable", "true")
    # xbmcplugin.setResolvedUrl(addon.handle, True, item)
    # return

    info = extract_source(page_url)

    item = xbmcgui.ListItem(info.title, offscreen=True)
    item.setPath(info.play_url)
    addon.logger.debug(info.play_url)

    # if 'dash' in video['best_fmt']:
    #     item.setProperty('inputstream', 'inputstream.adaptive')
    #     item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    # elif 'hls' in video['best_fmt']:
    #     item.setProperty('inputstream', 'inputstream.adaptive')
    #     item.setProperty('inputstream.adaptive.manifest_type', 'hls')

    item.setProperty('inputstream.adaptive.stream_selection_type', 'adaptive')
    item.setProperty('inputstream.adaptive.chooser_resolution_max', 'auto')
    item.setProperty('inputstream', 'inputstream.adaptive')
    item.setProperty('inputstream.adaptive.manifest_type', 'hls')
    # item.setMimeType('application/x-mpegURL')
    from urllib.parse import urlencode
    headers = urlencode(info.info.get('http_headers', {}))
    item.setProperty('inputstream.adaptive.manifest_headers', headers)
    item.setProperty('inputstream.adaptive.stream_headers', headers)

    xbmcplugin.setResolvedUrl(addon.handle, True, item)


def main():
    addon.dispatch()
