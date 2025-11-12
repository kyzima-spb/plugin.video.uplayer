import typing as t

from kodi_useful import (
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
    page: t.Annotated[int, Scope.QUERY] = 1,
):
    if page < 2:
        playlists_url = addon.url_for(list_playlists, channel_id=channel_id)
        playlists_item = xbmcgui.ListItem('Playlists')
        yield playlists_url, playlists_item, True

        shorts_url = addon.url_for(list_shorts, channel_id=channel_id)
        shorts_item = xbmcgui.ListItem('Shorts')
        yield shorts_url, shorts_item, True

    collection = rutube_session.get_videos(person_id=channel_id, page=page)
    addon.logger.debug(collection)
    yield from list_videos(collection)

    if collection.has_next:
        next_url = addon.url_for(channel, channel_id=channel_id, page=page + 1)
        item = xbmcgui.ListItem('Next page')
        yield next_url, item, True


@router.route
@Directory(
    content=Content.VIDEOS,
    cache_to_disk=False,
)
def list_playlists(
    addon: Addon,
    channel_id: t.Annotated[str, Scope.QUERY],
    page: t.Annotated[int, Scope.QUERY] = 1,
):
    collection = rutube_session.get_playlists(person_id=channel_id, page=page)

    for p in collection:
        url = addon.url_for(list_playlist_items, playlist_id=p['id'])
        item = xbmcgui.ListItem(p['title'])
        item.setArt({
            'thumb': p['thumbnail_url'],
            'fanart': p['thumbnail_url'],
        })
        yield url, item, True

    if collection.has_next:
        next_url = addon.url_for(list_playlists, channel_id=channel_id, page=page + 1)
        item = xbmcgui.ListItem('Next page')
        yield next_url, item, True


@router.route
@Directory(
    content=Content.VIDEOS,
    cache_to_disk=False,
)
def list_playlist_items(
    addon: Addon,
    playlist_id: t.Annotated[int, Scope.QUERY],
    page: t.Annotated[int, Scope.QUERY] = 1,
):
    collection = rutube_session.get_playlist_items(playlist_id=playlist_id, page=page)

    yield from list_videos(collection)

    if collection.has_next:
        next_url = addon.url_for(list_playlist_items, playlist_id=playlist_id, page=page + 1)
        item = xbmcgui.ListItem('Next page')
        yield next_url, item, True


@router.route
@Directory(
    content=Content.VIDEOS,
    cache_to_disk=False,
)
def list_shorts(
    addon: Addon,
    channel_id: t.Annotated[str, Scope.QUERY],
    page: t.Annotated[int, Scope.QUERY] = 1,
):
    collection = rutube_session.get_shorts(person_id=channel_id, page=page)

    yield from list_videos(collection)

    if collection.has_next:
        next_url = addon.url_for(list_shorts, channel_id=channel_id, page=page + 1)
        item = xbmcgui.ListItem('Next page')
        yield next_url, item, True


@router.route
def play_video(
    addon: Addon,
    # quality: t.Annotated[str, Scope.QUERY],
    video_id: t.Annotated[str, Scope.QUERY],
):
    video = rutube_session.get_video_by_id(video_id)
    url = video['video_balancer']['default']

    item = xbmcgui.ListItem(offscreen=True)
    item.setPath(url)
    item.setProperty('inputstream', 'inputstream.adaptive')
    item.setProperty('inputstream.adaptive.manifest_type', 'hls')

    xbmcplugin.setResolvedUrl(addon.handle, True, item)
