from codequick import Route, Resolver, Listitem, run, Script
from codequick.script import Settings
from codequick.utils import keyboard
from codequick.listing import Context
import xbmcgui

from .storage import Playlist, PlaylistItem


@Route.register
def root(plugin):
    yield Listitem.from_dict(create_playlist, label='Create playlist')
    yield Listitem.from_dict(list_playlist_items, label='Added')
    yield from list_playlists(plugin)


@Route.register
def list_playlists(plugin, offset=0):
    limit = Settings.get_int('items_per_page')

    for p in Playlist.select(limit=limit, offset=offset):
        ctx = Context()
        ctx.script(add_playlist_item, 'Add source', playlist_id=p.id)
        ctx.script(edit_playlist, 'Edit', playlist_id=p.id)
        ctx.script(delete_playlist, 'Delete', playlist_id=p.id)
        yield Listitem.from_dict(list_playlist_items, context=ctx, label=p.label, params={
            'playlist_id': p.id,
        })

    offset += limit
    total = Playlist.count()

    if total > offset:
        yield Listitem.next_page(callback=list_playlists, offset=offset)


@Route.register
def list_playlist_items(_, playlist_id=None, offset=0):
    if offset == 0:
        yield Listitem.from_dict(add_playlist_item, label='Add new item', params={
            'playlist_id': playlist_id,
        })

    limit = Settings.get_int('items_per_page')
    playlist_items = PlaylistItem.select(playlist_id=playlist_id, limit=limit, offset=offset)

    for i in playlist_items:
        ctx = Context()
        ctx.script(delete_playlist_item, 'Delete', item_id=i.id)
        yield Listitem.from_dict(play_video, label=i.label, context=ctx, params={
            'item_id': i.id,
        })

    offset += limit
    total_items = PlaylistItem.count(playlist_id=playlist_id)

    if total_items > offset:
        yield Listitem.next_page(playlist_id=playlist_id, offset=offset)


@Resolver.register
def play_video(plugin, item_id):
    """Воспроизводит видео файл."""
    source = PlaylistItem.get(item_id=item_id)
    video_url = plugin.extract_source(source.url)

    return Listitem.from_dict(
        video_url,
        label=source.label,
        # properties={
        #     'inputstream': 'inputstream.adaptive',
        #     'inputstream.adaptive.manifest_type': 'hls',
        # },
    )


@Script.register
def add_playlist_item(_, playlist_id=None):
    url = keyboard('Enter URL')
    if url:
        PlaylistItem(playlist_id=playlist_id, url=url, label=url).save()
        Script.notify('Playlist item', 'Created successfully')


@Script.register
def create_playlist(_):
    label = keyboard('Enter playlist label')
    if label:
        Playlist(label=label).save()
        Script.notify('Playlist', 'Created successfully')


@Script.register
def delete_playlist(_, playlist_id):
    if xbmcgui.Dialog().yesno('Confirm action', 'Are you sure you want to delete the playlist?'):
        Playlist.get(playlist_id).delete()
        Script.notify('Playlist', 'Deleted successfully')


@Script.register
def delete_playlist_item(_, item_id):
    if xbmcgui.Dialog().yesno('Confirm action', 'Are you sure you want to delete the item?'):
        PlaylistItem.get(item_id).delete()
        Script.notify('Playlist', 'Item deleted successfully')


@Script.register
def edit_playlist(_, playlist_id):
    p = Playlist.get(playlist_id=playlist_id)
    p.label = keyboard('Enter playlist label', default=p.label)
    if p.label:
        p.update()
        Script.notify('Playlist', 'Successfully updated')
    else:
        Script.notify('Playlist', 'Not changed')
