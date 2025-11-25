import typing as t

from kodi_useful import (
    create_next_item,
    current_addon,
    router,
    Addon,
    Directory,
)
from kodi_useful.enums import Content, Scope
import xbmcgui
import xbmcplugin
from yt_dlp_utils import YTDownloader

from .items import url_construct
from ..storage import Item, ItemType
from ..providers.rutube import rutube_session


@url_construct.register(ItemType.RUTUBE_CHANNEL)
def get_url_for_channel(item: Item) -> str:
    """Возвращает ссылку для отображения меню Rutube канала."""
    return current_addon.url_for(channel, channel_id=item.data['channel_id'])


@url_construct.register(ItemType.RUTUBE_PLAYLIST)
def get_url_for_playlist(item: Item) -> str:
    """Возвращает ссылку для отображения списка видео в плейлисте Rutube."""
    return current_addon.url_for(list_playlist_items, playlist_id=item.data['playlist_id'])


@url_construct.register(ItemType.RUTUBE_VIDEO)
def get_url_for_video(item: Item) -> str:
    """Возвращает ссылку для отображения видео."""
    return current_addon.url_for(play_video, video_id=item.data['video_id'])


@router.route
def download_video(
    author: t.Annotated[str, Scope.QUERY],
    page_url: t.Annotated[str, Scope.QUERY],
    download_dir: t.Annotated[str, Scope.SETTINGS],
):
    downloader = YTDownloader(download_dir)
    downloader.download(
        page_url,
        f'%(extractor)s/{author}/%(timestamp>%Y_%m_%d)s - %(title)s.%(ext)s',
        metadata={
            'artist': author,
        },
    )


def list_videos(iterable):
    for v in iterable:
        url = current_addon.url_for(play_video, video_id=v['id'])
        item = xbmcgui.ListItem(v['title'])
        item.setInfo('video', {
            'plot': v['description'],
            'duration': v['duration'],
            'genre': v['category']['name'],
        })
        item.setArt({
            'thumb': v['thumbnail_url'],
            'fanart': v['thumbnail_url'],
        })
        item.setProperty('IsPlayable', 'true')
        item.addContextMenuItems([
            (
                current_addon.localize('download'),
                'RunPlugin(%s)' % current_addon.url_for(
                    download_video,
                    author=v['author']['name'],
                    page_url=v['video_url'],
                ),
            ),
        ])
        yield url, item, False


@router.route
@Directory(
    content=Content.VIDEOS,
    cache_to_disk=False,
)
def channel(
    addon: Addon,
    channel_id: t.Annotated[str, Scope.QUERY],
    items_per_page: t.Annotated[int, Scope.SETTINGS],
    page: t.Annotated[int, Scope.QUERY] = 1,
):
    if page < 2:
        playlists_url = addon.url_for(list_playlists, channel_id=channel_id)
        playlists_item = xbmcgui.ListItem(addon.localize('Playlists'))
        yield playlists_url, playlists_item, True

        shorts_url = addon.url_for(list_shorts, channel_id=channel_id)
        shorts_item = xbmcgui.ListItem(addon.localize('Shorts'))
        yield shorts_url, shorts_item, True

    user_videos = rutube_session.get_videos(person_id=channel_id, limit=items_per_page, page=page)

    yield from list_videos(user_videos)

    if user_videos.next_page:
        yield create_next_item(
            addon.url_for(channel, channel_id=channel_id, page=user_videos.next_page)
        )


@router.route
@Directory(
    content=Content.VIDEOS,
    cache_to_disk=False,
)
def list_tv_channels(
    addon: Addon,
    items_per_page: t.Annotated[int, Scope.SETTINGS],
    page: t.Annotated[int, Scope.QUERY] = 1,
):
    channels = rutube_session.get_tv_channels(limit=items_per_page, page=page)

    yield from list_videos(channels)

    if channels.next_page:
        yield create_next_item(
            addon.url_for(list_tv_channels, page=channels.next_page)
        )


@router.route
@Directory(
    content=Content.VIDEOS,
    cache_to_disk=False,
)
def list_playlists(
    addon: Addon,
    channel_id: t.Annotated[str, Scope.QUERY],
    items_per_page: t.Annotated[int, Scope.SETTINGS],
    page: t.Annotated[int, Scope.QUERY] = 1,
):
    playlists = rutube_session.get_playlists(person_id=channel_id, limit=items_per_page, page=page)

    for p in playlists:
        url = addon.url_for(list_playlist_items, playlist_id=p['id'], title=p['title'])
        item = xbmcgui.ListItem(p['title'])
        item.setArt({
            'thumb': p['thumbnail_url'],
            'fanart': p['thumbnail_url'],
        })
        yield url, item, True

    if playlists.next_page:
        yield create_next_item(
            addon.url_for(list_playlists, channel_id=channel_id, page=playlists.next_page)
        )


@router.route
@Directory(
    content=Content.VIDEOS,
    cache_to_disk=False,
)
def list_playlist_items(
    addon: Addon,
    playlist_id: t.Annotated[int, Scope.QUERY],
    items_per_page: t.Annotated[int, Scope.SETTINGS],
    page: t.Annotated[int, Scope.QUERY] = 1,
):
    user_videos = rutube_session.get_playlist_items(playlist_id=playlist_id, limit=items_per_page, page=page)

    yield from list_videos(user_videos)

    if user_videos.next_page:
        yield create_next_item(
            addon.url_for(list_playlist_items, playlist_id=playlist_id, page=user_videos.next_page)
        )


@router.route
@Directory(
    content=Content.VIDEOS,
    cache_to_disk=False,
)
def list_shorts(
    addon: Addon,
    channel_id: t.Annotated[str, Scope.QUERY],
    items_per_page: t.Annotated[int, Scope.SETTINGS],
    page: t.Annotated[int, Scope.QUERY] = 1,
):
    short_videos = rutube_session.get_shorts(person_id=channel_id, limit=items_per_page, page=page)

    yield from list_videos(short_videos)

    if short_videos.next_page:
        yield create_next_item(
            addon.url_for(list_shorts, channel_id=channel_id, page=short_videos.next_page)
        )


@router.route
def play_video(
    addon: Addon,
    # quality: t.Annotated[str, Scope.QUERY],
    video_id: t.Annotated[str, Scope.QUERY],
):
    video = rutube_session.get_video_by_id(video_id)

    if video.best_quality_url is None:
        raise ValueError('Stream not found')

    item = xbmcgui.ListItem(offscreen=True)
    item.setPath(video.best_quality_url)
    item.setProperty('inputstream', 'inputstream.adaptive')
    item.setProperty('inputstream.adaptive.manifest_type', 'hls')

    xbmcplugin.setResolvedUrl(addon.handle, True, item)
