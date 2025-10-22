import typing as t

from kodi_useful import (
    create_next_element,
    current_addon,
    router,
    Addon,
    Directory,
)
from kodi_useful.gui import prompt
from kodi_useful.enums import Content, Scope
import xbmc
import xbmcgui

from ..storage import Playlist, PlaylistType
from ..providers import media_provider
from ..utils import URLConstructor


url_construct = URLConstructor()


@url_construct.register(PlaylistType.MANUAL)
def get_items_url(playlist: Playlist) -> str:
    """Возвращает ссылку для отображения элементов плейлиста."""
    return current_addon.url_for(
        'resources.lib.pages.playlist_items.list_playlist_items',
        playlist_id=playlist.id,
        title=playlist.title,
    )


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

    if addon.get_setting('boosty.enabled', bool):
        boosty_url = addon.url_for('resources.lib.pages.boosty.list_subscriptions')
        boosty_item = xbmcgui.ListItem('Boosty')
        boosty_item.setArt({'thumb': addon.get_path('resources/lib/assets/services/boosty.jpg')})
        boosty_item.setInfo('video', {'plot': addon.localize('boosty.description')})
        yield boosty_url, boosty_item, True

    added_url = addon.url_for(
        'resources.lib.pages.playlist_items.list_playlist_items',
        title='Added',
    )
    added_item = xbmcgui.ListItem(label='Added')
    yield added_url, added_item, True

    playlists = Playlist.select(limit=items_per_page + 1, offset=offset)
    render_next_page = len(playlists) > items_per_page

    for p in playlists[:items_per_page]:
        url = url_construct(p.type_name, p)
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
        media_provider.create_model(title_or_url.value, model_class=Playlist).save()
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
