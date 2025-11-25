from functools import wraps
import typing as t

from kodi_useful import (
    alert,
    create_next_item,
    current_addon,
    router,
    Addon,
    Directory,
)
from kodi_useful.enums import Content, Scope
from kodi_useful.utils import open_browser
import xbmcgui
import xbmcplugin

from .items import url_construct
from ..providers.youtube import youtube_session, YouTubeApiError
from ..storage import Item, ItemType
from ..utils import get_icon


def catch_api_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except YouTubeApiError as err:
            alert(current_addon.localize('%s: Api Error', 'YouTube'), err.message)
            current_addon.logger.error(f'[{err.code}]: {err.message}, {err.errors}')
            xbmcplugin.endOfDirectory(current_addon.handle, False, False)
    return wrapper


@url_construct.register(ItemType.YOUTUBE_CHANNEL)
def get_url_for_channel(item: Item) -> str:
    """Возвращает ссылку для отображения меню YouTube канала."""
    return current_addon.url_for(
        list_channel,
        channel_id=item.data['channel_id'],
        upload_playlist_id=item.data['upload_playlist_id'],
        title=item.title,
    )


@url_construct.register(ItemType.YOUTUBE_PLAYLIST)
def get_url_for_playlist(item: Item) -> str:
    """Возвращает ссылку для отображения списка видео в плейлисте YouTube."""
    return current_addon.url_for(list_playlist_items, playlist_id=item.data['playlist_id'], title=item.title)


@url_construct.register(ItemType.YOUTUBE_VIDEO)
def get_url_for_video(item: Item) -> str:
    """Возвращает ссылку для отображения видео."""
    return current_addon.url_for(play_video, video_id=item.data['video_id'])


def list_videos(iterable):
    for v in iterable:
        url = current_addon.url_for(play_video, video_id=v['id'])
        item = xbmcgui.ListItem(v.title)
        item.setInfo('video', {
            'plot': v.description,
            'duration': v.duration,
            'aired': v.published.strftime('%Y-%m-%d %H:%M:%S'),
        })
        item.setArt({
            'thumb': v.thumbnail,
            'fanart': v.cover,
        })
        item.setProperty('IsPlayable', 'true')
        yield url, item, False


@router.route
@catch_api_error
@Directory(
    content=Content.VIDEOS,
    cache_to_disk=current_addon.debug,
)
def list_channel(
    addon: Addon,
    channel_id: t.Annotated[str, Scope.QUERY],
    upload_playlist_id: t.Annotated[str, Scope.QUERY],
    items_per_page: t.Annotated[int, Scope.SETTINGS],
    next_page: t.Annotated[str, Scope.QUERY] = '',
    title: t.Annotated[str, Scope.QUERY] = '',
):
    if not next_page:
        item_title = addon.localize('Playlists')
        playlists_url = addon.url_for(list_playlists, channel_id=channel_id, title=f'{title} - {item_title}')
        playlists_item = xbmcgui.ListItem(item_title)
        playlists_item.setArt({'icon': get_icon('order_play.png')})
        yield playlists_url, playlists_item, True

    #     shorts_url = addon.url_for(list_shorts, channel_id=channel_id)
    #     shorts_item = xbmcgui.ListItem(addon.localize('Shorts'))
    #     yield shorts_url, shorts_item, True

    videos = youtube_session.get_videos(
        playlist_id=upload_playlist_id, limit=items_per_page, page_token=next_page,
    )

    yield from list_videos(videos)

    if videos.next_page:
        yield create_next_item(
            addon.url_for(
                list_channel,
                channel_id=channel_id,
                upload_playlist_id=upload_playlist_id,
                items_per_page=items_per_page,
                next_page=videos.next_page,
                title=title,
            )
        )


@router.route
@Directory(
    content=Content.VIDEOS,
    cache_to_disk=current_addon.debug,
)
def list_playlists(
    addon: Addon,
    channel_id: t.Annotated[str, Scope.QUERY],
    items_per_page: t.Annotated[int, Scope.SETTINGS],
    next_page: t.Annotated[str, Scope.QUERY] = '',
):
    playlists = youtube_session.get_playlists(channel_id, limit=items_per_page, page_token=next_page)

    for p in playlists:
        url = addon.url_for(list_playlist_items, playlist_id=p['id'], title=p.title)
        item = xbmcgui.ListItem(p.title)
        item.setInfo('video', {
            'plot': p.description,
            'aired': p.published.strftime('%Y-%m-%d %H:%M:%S'),
        })
        item.setArt({
            'thumb': p.thumbnail or get_icon('order_play.png'),
            'fanart': p.cover,
        })
        yield url, item, True

    if playlists.next_page:
        yield create_next_item(
            addon.url_for(list_playlists, channel_id=channel_id, next_page=playlists.next_page)
        )


@router.route
@Directory(
    content=Content.VIDEOS,
    cache_to_disk=current_addon.debug,
)
def list_playlist_items(
    addon: Addon,
    playlist_id: t.Annotated[str, Scope.QUERY],
    items_per_page: t.Annotated[int, Scope.SETTINGS],
    next_page: t.Annotated[str, Scope.QUERY] = '',
    title: t.Annotated[str, Scope.QUERY] = '',
):
    videos = youtube_session.get_videos(
        playlist_id=playlist_id, limit=items_per_page, page_token=next_page,
    )

    yield from list_videos(videos)

    if videos.next_page:
        yield create_next_item(
            addon.url_for(
                list_playlist_items,
                playlist_id=playlist_id,
                items_per_page=items_per_page,
                next_page=videos.next_page,
                title=title,
            )
        )


@router.route
def play_video(
    addon: Addon,
    video_id: t.Annotated[str, Scope.QUERY],
):
    open_browser('https://youtu.be/%s' % video_id)
    xbmcplugin.setResolvedUrl(addon.handle, True, xbmcgui.ListItem())
