from __future__ import annotations
from contextlib import suppress
import json
import pathlib
import sys
from urllib.parse import parse_qsl, urlencode

import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
from xbmcvfs import translatePath

from . import settings
from .log import get_logger
from .storage import Playlist, PlaylistItem
from .utils import extract_source


addon = xbmcaddon.Addon()

# Get a plugin handle as an integer number.
HANDLE = int(sys.argv[1])
# Get addon base path
ADDON_PATH = pathlib.Path(translatePath(addon.getAddonInfo('path')))
# GLOBAL_PATH = translatePath("special://home/")

logger = get_logger(__name__)


class Router:
    def __init__(
        self,
        plugin_url: str,
        index_route: str = '',
        route_param_name: str = 'action',
    ) -> None:
        """
        Arguments:
            plugin_url str the plugin url in plugin:// notation.
        """
        self.plugin_url = plugin_url
        self.index_route = index_route
        self.route_param_name = route_param_name
        self.routes = {}

    def dispatch(self, qs: str):
        def loads(v):
            with suppress(Exception):
                v = json.loads(v)
            return v

        q = {k: loads(v) for k, v in parse_qsl(qs.strip('?'))}

        try:
            route_name = q.pop(self.route_param_name)
        except KeyError:
            route_name = self.index_route

        func = self.routes[route_name]
        return func(**q)

    def route(self, name: str = ''):
        def decorator(func):
            func.__route_name__ = name or self.index_route
            self.routes[func.__route_name__] = func
            return func
        return decorator

    def url_for(self, func, **kwargs) -> str:
        """
        Returns a URL for calling the plugin recursively from the given set of keyword arguments.

        Arguments:
            action str
            kwargs dict "argument=value" pairs
        """
        def dumps(v):
            if not isinstance(v, str):
                v = json.dumps(v)
            return v

        kwargs[self.route_param_name] = func.__route_name__

        return '%s?%s' % (self.plugin_url, urlencode([
            (k, dumps(v)) for k, v in kwargs.items()
        ]))


router = Router(sys.argv[0])


@router.route()
def list_playlists(offset=0):
    limit = settings.get_int('items_per_page')

    xbmcplugin.setPluginCategory(HANDLE, 'Playlists')
    xbmcplugin.setContent(HANDLE, 'videos')

    if offset < 1:
        url = router.url_for(create_playlist)
        create_action = xbmcgui.ListItem(label='[B]Create playlist[/B]')
        create_action.setProperty('IsPlayable', 'false')
        xbmcplugin.addDirectoryItem(HANDLE, url, create_action)

    url = router.url_for(list_playlist_items)
    added_item = xbmcgui.ListItem(label='Added')
    xbmcplugin.addDirectoryItem(HANDLE, url, added_item, isFolder=True)

    for p in Playlist.select(limit=limit, offset=offset):
        url = router.url_for(list_playlist_items, playlist_id=p.id)
        item = xbmcgui.ListItem(label=p.label)
        item.addContextMenuItems([
            (
                'Add source',
                'RunPlugin(%s)' % router.url_for(add_playlist_item, playlist_id=p.id),
            ),
            (
                'Edit',
                'RunPlugin(%s)' % router.url_for(edit_playlist, playlist_id=p.id),
            ),
            (
                'Delete',
                'RunPlugin(%s)' % router.url_for(delete_playlist, playlist_id=p.id),
            ),
        ])
        xbmcplugin.addDirectoryItem(HANDLE, url, item, isFolder=True)

    offset += limit
    total = Playlist.count()

    if total > offset:
        url = router.url_for(list_playlists, offset=offset)
        label = 'Next page (%d)' % (offset // limit)
        next_page_item = xbmcgui.ListItem(label)
        info_tag = next_page_item.getVideoInfoTag()
        info_tag.setPlot(label)
        xbmcplugin.addDirectoryItem(HANDLE, url, next_page_item, isFolder=True, totalItems=total)

    xbmcplugin.endOfDirectory(HANDLE)


@router.route('playlists/create')
def create_playlist():
    kb = xbmc.Keyboard('', 'Enter playlist label')
    kb.doModal()
    if kb.isConfirmed() and kb.getText():
        Playlist(label=kb.getText()).save()
        xbmc.executebuiltin('Container.Refresh()')
        xbmcgui.Dialog().notification('Playlist', 'Created successfully')


@router.route('playlists/delete')
def delete_playlist(playlist_id):
    if xbmcgui.Dialog().yesno('Confirm action', 'Are you sure you want to delete the playlist?'):
        Playlist.get(playlist_id=playlist_id).delete()
        xbmc.executebuiltin('Container.Refresh()')
        xbmcgui.Dialog().notification('Playlist', 'Deleted successfully')


@router.route('playlists/edit')
def edit_playlist(playlist_id):
    p = Playlist.get(playlist_id=playlist_id)
    kb = xbmc.Keyboard(p.label, 'Enter playlist label')
    kb.doModal()
    if kb.isConfirmed():
        p.label = kb.getText()
        if p.label:
            p.update()
            xbmc.executebuiltin('Container.Refresh()')
            xbmcgui.Dialog().notification('Playlist', 'Successfully updated')
        else:
            xbmcgui.Dialog().notification('Playlist', 'Not changed')


@router.route('playlists/items')
def list_playlist_items(playlist_id=None, offset=0):
    if playlist_id is None:
        xbmcplugin.setPluginCategory(HANDLE, 'Added')
    else:
        p = Playlist.get(playlist_id=playlist_id)
        xbmcplugin.setPluginCategory(HANDLE, p.label)

    xbmcplugin.setContent(HANDLE, 'videos')

    if offset < 1:
        url = router.url_for(add_playlist_item, playlist_id=playlist_id)
        create_action = xbmcgui.ListItem(label='[B]Add new item[/B]')
        create_action.setProperty('IsPlayable', 'false')
        xbmcplugin.addDirectoryItem(HANDLE, url, create_action)

    limit = settings.get_int('items_per_page')
    playlist_items = PlaylistItem.select(playlist_id=playlist_id, limit=limit, offset=offset)

    for i in playlist_items:
        url = router.url_for(play_video, item_id=i.id)
        item = xbmcgui.ListItem(i.label)
        item.setProperty('IsPlayable', 'true')
        item.addContextMenuItems([
            ('Delete', 'RunPlugin(%s)' % router.url_for(delete_playlist_item, item_id=i.id)),
        ])
        xbmcplugin.addDirectoryItem(HANDLE, url, item)

    offset += limit
    total = PlaylistItem.count(playlist_id=playlist_id)

    if total > offset:
        url = router.url_for(list_playlist_items, offset=offset)
        label = 'Next page (%d)' % (offset // limit)
        next_page_item = xbmcgui.ListItem(label)
        info_tag = next_page_item.getVideoInfoTag()
        info_tag.setPlot(label)
        xbmcplugin.addDirectoryItem(HANDLE, url, next_page_item, isFolder=True, totalItems=total)

    xbmcplugin.endOfDirectory(HANDLE)


@router.route('playlists/items/create')
def add_playlist_item(playlist_id):
    logger.debug(type(playlist_id))
    # kb = xbmc.Keyboard('https://www.youtube.com/watch?v=G8qPHi4zNms', 'Enter URL')
    # kb = xbmc.Keyboard('https://vk.com/video190953452_456239281', 'Enter URL')
    # kb = xbmc.Keyboard('https://vk.com/video_ext.php?oid=190953452&id=456239281', 'Enter URL')
    # kb = xbmc.Keyboard('https://vk.com/video_ext.php?oid=-215555758&id=456239025', 'Enter URL')
    # kb = xbmc.Keyboard('https://rutube.ru/video/94c30ec3be9e90ed13dc2b067a216508/', 'Enter URL')
    kb = xbmc.Keyboard('', 'Enter URL')
    kb.doModal()
    if kb.isConfirmed() and kb.getText():
        try:
            PlaylistItem(playlist_id=playlist_id, url=kb.getText(), label=kb.getText()).save()
        except Exception as err:
            logger.debug(err)
        xbmc.executebuiltin('Container.Refresh()')
        xbmcgui.Dialog().notification('Playlist item', 'Created successfully')


@router.route('playlists/items/delete')
def delete_playlist_item(item_id):
    if xbmcgui.Dialog().yesno('Confirm action', 'Are you sure you want to delete the item?'):
        PlaylistItem.get(item_id=item_id).delete()
        xbmc.executebuiltin('Container.Refresh()')
        xbmcgui.Dialog().notification('Playlist', 'Item deleted successfully')


@router.route('play')
def play_video(item_id):
    """Воспроизводит видео файл."""
    source = PlaylistItem.get(item_id=item_id)

    # path = 'https://ia600301.us.archive.org/8/items/CarnivalofSouls/CarnivalOfSouls_512kb.mp4'
    path = extract_source(source.url)
    play_item = xbmcgui.ListItem(offscreen=True)
    play_item.setPath(path)
    # Pass the item to the Kodi player
    xbmcplugin.setResolvedUrl(HANDLE, True, listitem=play_item)


def main():
    router.dispatch(sys.argv[2])
