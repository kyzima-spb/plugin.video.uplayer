import typing as t

from kodi_useful import (
    create_next_element,
    router,
    Addon,
    Directory,
)
from kodi_useful.gui import prompt
from kodi_useful.enums import Content, Scope
import xbmc
import xbmcgui

from ..storage import Playlist, PlaylistType


@router.route(is_root=True)
@Directory(
    ltitle='playlists',
    content=Content.VIDEOS,
    cache_to_disk=False,
)
def list_playlists(
    addon: Addon,
    items_per_page: t.Annotated[int, Scope.SETTINGS],
    offset: t.Annotated[int, Scope.QUERY] = 0,
):
    if offset < 1:
        create_url = addon.url_for(create_playlist)
        create_action = xbmcgui.ListItem(label='[B]Create playlist[/B]')
        create_action.setProperty('IsPlayable', 'false')
        yield create_url, create_action, False

    added_url = addon.url_for(
        'resources.lib.pages.playlist_items.list_playlist_items',
        title='Added',
    )
    added_item = xbmcgui.ListItem(label='Added')
    yield added_url, added_item, True

    playlists = Playlist.select(limit=items_per_page + 1, offset=offset)
    render_next_page = len(playlists) > items_per_page

    for p in playlists[:items_per_page]:
        if p.type_name == PlaylistType.MANUAL:
            url = addon.url_for(
                'resources.lib.pages.playlist_items.list_playlist_items',
                playlist_id=p.id,
                title=p.title,
            )
        elif p.type_name == PlaylistType.RUTUBE_CHANNEL:
            url = addon.url_for(
                'resources.lib.pages.rutube.channel',
                channel_id=p.data['channel_id'],
            )
        elif p.type_name == PlaylistType.RUTUBE_PLAYLIST:
            url = addon.url_for(
                'resources.lib.pages.rutube.list_playlist_items',
                playlist_id=p.data['playlist_id']
            )
        else:
            continue

        item = xbmcgui.ListItem(label=p.title)
        item.setInfo('video', {
            'plot': p.description,
        })
        item.setArt({
            'thumb': p.cover,
        })
        # item.setProperty('IsPlayable', 'false')
        item.addContextMenuItems([
            (
                'Add source',
                'RunPlugin(%s)' % addon.url_for(
                    'resources.lib.pages.playlist_items.add_playlist_item',
                    playlist_id=p.id
                ),
            ),
            (
                'Edit',
                'RunPlugin(%s)' % addon.url_for(edit_playlist, playlist_id=p.id),
            ),
            (
                'Delete',
                'RunPlugin(%s)' % addon.url_for(delete_playlist, playlist_id=p.id),
            ),
        ])
        yield url, item, True

    if render_next_page:
        offset += items_per_page
        yield create_next_element(list_playlists, offset=offset)


@router.route
def create_playlist():
    title_or_url = prompt('Enter playlist title or URL', required=True)

    if title_or_url:
        Playlist.create(title_or_url.value).save()
        xbmc.executebuiltin('Container.Refresh()')


@router.route
def delete_playlist(
    playlist_id: t.Annotated[str, Scope.QUERY],
):
    if xbmcgui.Dialog().yesno('Confirm action', 'Are you sure you want to delete the playlist?'):
        playlist = Playlist.find(playlist_id)

        if playlist is not None:
            playlist.delete()
            xbmc.executebuiltin('Container.Refresh()')


@router.route
def edit_playlist(
    playlist_id: t.Annotated[str, Scope.QUERY],
):
    playlist = Playlist.find(playlist_id)

    title = prompt('Enter playlist label', required=True, default=playlist.title)

    if title:
        playlist.title = title.value
        playlist.save()
        xbmc.executebuiltin('Container.Refresh()')
