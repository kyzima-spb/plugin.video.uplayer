import typing as t

from kodi_useful import (
    current_addon,
    router,
    Addon,
    Directory,
)
from kodi_useful.enums import Content, Scope
import xbmcgui
from yt_dlp_utils import YTDownloader

from .. import rutube


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
        url = current_addon.url_for('resources.lib.main.play_video', page_url=v.video_url)
        item = xbmcgui.ListItem(v.title)
        item.setInfo('video', {
            'plot': v.description,
            'duration': v.duration,
            'genre': v.category['name'],
        })
        item.setArt({
            'thumb': v.thumbnail_url,
        })
        item.setProperty('IsPlayable', 'true')
        item.addContextMenuItems([
            (
                current_addon.localize('download'),
                'RunPlugin(%s)' % current_addon.url_for(
                    download_video,
                    author=v.author['name'],
                    page_url=v.video_url,
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

    collection = rutube.Videos.list(person_id=channel_id, page=page)
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
    collection = rutube.Playlists.list(person_id=channel_id, page=page)

    for p in collection:
        url = addon.url_for(list_playlist_items, playlist_id=p.id)
        item = xbmcgui.ListItem(p.title)
        item.setArt({
            'thumb': p.thumbnail_url,
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
    collection = rutube.PlaylistItems.list(playlist_id=playlist_id, page=page)

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
    collection = rutube.Shorts.list(person_id=channel_id, page=page)

    yield from list_videos(collection)

    if collection.has_next:
        next_url = addon.url_for(list_shorts, channel_id=channel_id, page=page + 1)
        item = xbmcgui.ListItem('Next page')
        yield next_url, item, True
