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

from ..storage import PlaylistItem


@router.route
@Directory(
    content=Content.VIDEOS,
    cache_to_disk=False,
)
def list_playlist_items(
    addon: Addon,
    items_per_page: t.Annotated[int, Scope.SETTINGS],
    offset: t.Annotated[int, Scope.QUERY] = 0,
    playlist_id: t.Annotated[t.Optional[str], Scope.QUERY] = None,
):
    if offset < 1:
        create_url = addon.url_for(add_playlist_item, playlist_id=playlist_id)
        create_action = xbmcgui.ListItem(label='[B]Add new item[/B]')
        create_action.setProperty('IsPlayable', 'false')
        yield create_url, create_action, False

    playlist_items = PlaylistItem.select(
        playlist_id=playlist_id,
        limit=items_per_page + 1,
        offset=offset,
    )
    render_next_page = len(playlist_items) > items_per_page

    for i in playlist_items[:items_per_page]:
        url = addon.url_for('resources.lib.main.play_video', page_url=i.url)
        item = xbmcgui.ListItem(i.title)
        item.setProperty('IsPlayable', 'true')
        item.addContextMenuItems([
            ('Delete', 'RunPlugin(%s)' % addon.url_for(delete_playlist_item, item_id=i.id)),
        ])
        yield url, item, False

    if render_next_page:
        offset += items_per_page
        yield create_next_element(list_playlist_items, offset=offset)


@router.route
def add_playlist_item(
    playlist_id: t.Annotated[t.Optional[str], Scope.QUERY] = None,
):
    # url = 'https://www.youtube.com/watch?v=G8qPHi4zNms'
    # url = 'https://vk.com/video190953452_456239281'
    # url = 'https://vk.com/video_ext.php?oid=190953452&id=456239281'
    # url = 'https://rutube.ru/video/94c30ec3be9e90ed13dc2b067a216508/'
    url = prompt('Enter URL', required=True)

    if url:
        PlaylistItem(playlist_id=playlist_id, url=url.value).save()
        xbmc.executebuiltin('Container.Refresh()')


@router.route
def delete_playlist_item(
    item_id: t.Annotated[str, Scope.QUERY] = None,
):
    if xbmcgui.Dialog().yesno('Confirm action', 'Are you sure you want to delete the item?'):
        PlaylistItem.find(item_id).delete()
        xbmc.executebuiltin('Container.Refresh()')
