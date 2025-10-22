import typing as t

import boosty_api
from kodi_useful import (
    create_next_item,
    current_addon,
    router,
    Addon,
    Directory,
)
from kodi_useful import fs, gui
from kodi_useful.enums import Content, Scope
import xbmc
import xbmcgui
import xbmcplugin

from .playlists import url_construct
from ..storage import Playlist, PlaylistType
from ..providers.boosty import (
    boosty_login, boosty_session, catch_api_error, download, extract_info
)


@url_construct.register(PlaylistType.BOOSTY)
def get_index_url(playlist: Playlist) -> str:
    """Возвращает ссылку для отображения меню Boosty канала."""
    return current_addon.url_for(index, username=playlist.data['username'])


@router.route
@catch_api_error
def download_video(
    username: t.Annotated[str, Scope.QUERY],
    post_id: t.Annotated[str, Scope.QUERY],
    media_idx: t.Annotated[int, Scope.QUERY],
):
    download(username, post_id, media_idx)


@router.route
@catch_api_error
def play_saved(
    username: t.Annotated[str, Scope.QUERY],
    post_id: t.Annotated[str, Scope.QUERY],
    media_idx: t.Annotated[int, Scope.QUERY],
):
    info = extract_info(username, post_id, media_idx)

    if fs.exists(info['target_file']):
        xbmc.Player().play(info['target_file'])
    else:
        gui.notification('File not found', info['target_file'])


@router.route
@catch_api_error
@boosty_login
@Directory(
    content=Content.VIDEOS,
    cache_to_disk=False,
)
def index(
    addon: Addon,
    username: t.Annotated[str, Scope.QUERY],
    items_per_page: t.Annotated[int, Scope.SETTINGS],
    only_allowed: t.Annotated[bool, Scope.SETTINGS, 'boosty.only_allowed'],
    offset: t.Annotated[t.Optional[str], Scope.QUERY] = None,
):
    media_files = boosty_session.get_media(
        username=username,
        limit=items_per_page,
        offset=offset,
        media_type=boosty_api.MediaType.VIDEO,
        only_allowed=only_allowed,
    )

    for media in media_files:
        post = media['post']

        item = xbmcgui.ListItem(post['title'])

        video_info = item.getVideoInfoTag()
        video_info.setPlot(post['teaser'].description)

        cxt_menu = [
            (
                addon.localize('Play saved file'),
                'RunPlugin(%s)' % addon.url_for(
                    play_saved,
                    username=media_files.extra['username'],
                    post_id=post['id'],
                    media_idx=media['idx'],
                ),
            ),
        ]

        if not post['hasAccess']:
            url = addon.url_for(
                'resources.lib.main.notification',
                title=addon.localize('Access denied'),
                message=addon.localize('Subscription is required'),
                level=xbmcgui.NOTIFICATION_ERROR,
            )
            item.setArt({
                'thumb': post['teaser'].get_thumbnail(
                    addon.get_path('resources', 'lib', 'assets', 'icons', 'lock.png')
                ),
            })
        else:
            quality, play_url = boosty_api.utils.select_best_quality(media['playerUrls'], skip_dash=True)
            url = addon.url_for(play_video, quality=quality, url=play_url)

            video_info.setDuration(media['duration'])
            item.setArt({'thumb': media['preview']})
            item.setProperty('IsPlayable', 'true')

            cxt_menu.append((
                addon.localize('Download'),
                'RunPlugin(%s)' % addon.url_for(
                    download_video,
                    username=media_files.extra['username'],
                    post_id=post['id'],
                    media_idx=media['idx'],
                )
            ))

        item.addContextMenuItems(cxt_menu)

        yield url, item, False

    if not media_files.is_last:
        yield create_next_item(addon.url_for(
            index,
            username=username,
            items_per_page=items_per_page,
            offset=media_files.offset
        ))


@router.route
def add_to_homepage(
    addon: Addon,
    username: t.Annotated[str, Scope.QUERY],
):
    Playlist.create(f'https://boosty.to/{username}/').save()
    xbmcgui.Dialog().notification(
        heading=addon.localize('success'),
        message=addon.localize('playlist.added'),
        icon='info',
        time=3000,
    )


@router.route
@catch_api_error
@boosty_login
@Directory(
    content=Content.VIDEOS,
    cache_to_disk=False,
    ltitle='Subscriptions',
)
def list_subscriptions(
    addon: Addon,
    items_per_page: t.Annotated[int, Scope.SETTINGS],
    offset: t.Annotated[int, Scope.QUERY] = 0,
):
    subscriptions = boosty_session.get_subscriptions(limit=items_per_page, offset=offset)

    for person in subscriptions:
        username = person['blog']['blogUrl']
        title = person['blog']['owner']['name']

        url = addon.url_for(index, username=username, title=title)
        item = xbmcgui.ListItem(title)
        item.setInfo('video', {
            'plot': f'[B]{title}[/B]\n\n{person["blog"]["title"]}',
        })
        item.setArt({
            'thumb': person['blog']['owner']['avatarUrl'],
            'fanart': person['blog']['coverUrl'],
        })
        item.addContextMenuItems([
            (
                addon.localize('add.to.homepage'),
                'RunPlugin(%s)' % addon.url_for(add_to_homepage, username=username),
            ),
        ])
        yield url, item, True

    if not subscriptions.is_last:
        yield create_next_item(addon.url_for(
            list_subscriptions,
            items_per_page=items_per_page,
            offset=offset + items_per_page
        ))


@router.route
@catch_api_error
def logout(addon: Addon):
    boosty_session.logout()


@router.route
@catch_api_error
def play_video(
    addon: Addon,
    quality: t.Annotated[str, Scope.QUERY],
    url: t.Annotated[str, Scope.QUERY],
):
    headers = {}
    headers['User-Agent'] = boosty_session.user_agent

    url += '|' + '&'.join([f'{k}={v}' for k, v in headers.items()])

    item = xbmcgui.ListItem(offscreen=True)
    item.setPath(url)

    if quality == boosty_api.Quality.DASH:
        item.setProperty('inputstream', 'inputstream.adaptive')
        item.setProperty('inputstream.adaptive.manifest_type', 'mpd')
    elif quality == boosty_api.Quality.HLS:
        item.setProperty('inputstream', 'inputstream.adaptive')
        item.setProperty('inputstream.adaptive.manifest_type', 'hls')

    xbmcplugin.setResolvedUrl(addon.handle, True, item)
