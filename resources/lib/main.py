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
    info = extract_source(page_url)

    item = xbmcgui.ListItem(info.title, offscreen=True)
    item.setPath(info.play_url)

    # if 'dash' in video['best_fmt']:
    #     item.setProperty('inputstream', 'inputstream.adaptive')
    #     item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    # elif 'hls' in video['best_fmt']:
    #     item.setProperty('inputstream', 'inputstream.adaptive')
    #     item.setProperty('inputstream.adaptive.manifest_type', 'hls')

    item.setProperty('inputstream', 'inputstream.adaptive')
    item.setProperty('inputstream.adaptive.manifest_type', 'hls')

    xbmcplugin.setResolvedUrl(addon.handle, True, item)


def main():
    addon.dispatch()
