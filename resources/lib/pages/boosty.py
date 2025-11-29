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

from .items import url_construct
from ..storage import Item, ItemType
from ..providers import media_provider
from ..providers.boosty import (
    boosty_login, boosty_session, catch_api_error, download, extract_info
)


@url_construct.register(ItemType.BOOSTY_PROFILE)
def get_url_for_profile(item: Item) -> str:
    """Возвращает ссылку для отображения медиа из профиля пользователя Boosty."""
    return current_addon.url_for(index, username=item.data['username'])


@url_construct.register(ItemType.BOOSTY_POST)
def get_url_for_post(item: Item) -> str:
    """Возвращает ссылку для отображения медиа из поста пользователя Boosty."""
    return current_addon.url_for(index, username=item.data['username'], post_id=item.data['post_id'])


@url_construct.register(ItemType.BOOSTY_VIDEO)
def get_url_for_media(item: Item) -> str:
    """Возвращает ссылку для отображения одного медиа из поста пользователя Boosty."""
    return current_addon.url_for(
        play_video_by_id,
        username=item.data['username'],
        post_id=item.data['post_id'],
        media_id=item.data['media_id'],
    )


@router.route
@catch_api_error
def download_video(
    username: t.Annotated[str, Scope.QUERY],
    post_id: t.Annotated[str, Scope.QUERY],
    media_id: t.Annotated[str, Scope.QUERY],
):
    download(username, post_id, media_id)


@router.route
@catch_api_error
def play_saved(
    username: t.Annotated[str, Scope.QUERY],
    post_id: t.Annotated[str, Scope.QUERY],
    media_id: t.Annotated[str, Scope.QUERY],
):
    info = extract_info(username, post_id, media_id)

    if fs.exists(info['target_file']):
        xbmc.Player().play(info['target_file'])
    else:
        gui.notification('File not found', info['target_file'])


@router.route
@catch_api_error
@boosty_login
@Directory(content=Content.VIDEOS)
def index(
    addon: Addon,
    username: t.Annotated[str, Scope.QUERY],
    items_per_page: t.Annotated[int, Scope.SETTINGS],
    only_allowed: t.Annotated[bool, Scope.SETTINGS, 'boosty.only_allowed'],
    offset: t.Annotated[t.Optional[str], Scope.QUERY] = None,
    post_id: t.Annotated[t.Optional[str], Scope.QUERY] = None,
):
    if post_id is None:
        media_files = boosty_session.get_media(
            username=username,
            limit=items_per_page,
            offset=offset,
            media_type=boosty_api.MediaType.VIDEO,
            only_allowed=only_allowed,
        )
    else:
        post = boosty_session.get_post(username=username, post_id=post_id)
        media_files = post.get_media(media_type=boosty_api.MediaType.VIDEO)

    for media in media_files:
        post = media['post']

        item = xbmcgui.ListItem(post['title'])

        video_info = item.getVideoInfoTag()
        video_info.setPlot(post.teaser.description)

        cxt_menu = [
            (
                addon.localize('Play saved file'),
                'RunPlugin(%s)' % addon.url_for(
                    play_saved,
                    username=media.username,
                    post_id=post['id'],
                    media_id=media['id'],
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
                'thumb': post.teaser.get_thumbnail(
                    addon.get_path('resources', 'lib', 'assets', 'icons', 'lock.png')
                ),
            })
        else:
            quality, play_url = boosty_api.utils.select_best_quality(media['playerUrls'], skip_dash=True)
            url = addon.url_for(play_video, quality=quality, url=play_url)

            video_info.setDuration(media['duration'])
            item.setArt({'thumb': media['preview'], 'fanart': media['preview']})
            item.setProperty('IsPlayable', 'true')

            cxt_menu.append((
                addon.localize('Download'),
                'RunPlugin(%s)' % addon.url_for(
                    download_video,
                    username=media.username,
                    post_id=post['id'],
                    media_id=media['id'],
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
    media_provider.create_item(f'https://boosty.to/{username}/').save()
    xbmcgui.Dialog().notification(
        heading=addon.localize('success'),
        message=addon.localize('playlist.added'),
        icon='info',
        time=3000,
    )


@router.route
@catch_api_error
@boosty_login
@Directory(content=Content.VIDEOS, ltitle='Subscriptions')
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


@router.route
@catch_api_error
def play_video_by_id(
    addon: Addon,
    username: t.Annotated[str, Scope.QUERY],
    post_id: t.Annotated[str, Scope.QUERY],
    media_id: t.Annotated[str, Scope.QUERY],
):
    media = boosty_session.get_media_by_id(username=username, post_id=post_id, media_id=media_id)

    quality, play_url = boosty_api.utils.select_best_quality(media['playerUrls'], skip_dash=True)
    play_video(addon, quality, play_url)
