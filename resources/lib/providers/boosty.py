from functools import wraps
import os
import typing as t

import boosty_api
from boosty_api.enums import Quality
from boosty_api.utils import extract_text
from kodi_useful import alert, current_addon, prompt, Addon
from kodi_useful import gui
import xbmcplugin
from yt_dlp_utils import YTDownloader
from yt_dlp_utils.enums import Quality as YTQuality

from ..storage import PlaylistType


def adapter(url):
    if url.startswith('https://boosty.to/'):
        user = boosty_session.get_profile_by_url(url)
        return {
            'type_name': PlaylistType.BOOSTY,
            'title': f"{user['owner']['name']} - {user['title']}",
            'description': extract_text(user['description']),
            'cover': user['owner']['avatarUrl'],
            'username': user['blogUrl'],
            'url': f"https://boosty.to/{user['blogUrl']}/",
        }
    else:
        return None


def select_file_url(player_urls: t.Sequence[t.Dict[str, t.Any]]) -> t.Optional[str]:
    files = boosty_api.utils.get_allowed_quality(player_urls, skip_dash=True, skip_hls=True)

    yt_addon = Addon.get_instance('script.module.yt-dlp')
    yt_quality_map = {
        Quality.SD_144: YTQuality.SD_144,
        Quality.SD_240: YTQuality.SD_240,
        Quality.SD_360: YTQuality.SD_360,
        Quality.SD_480: YTQuality.SD_480,
        Quality.HD: YTQuality.HD_720,
        Quality.FHD: YTQuality.FHD_1080,
        Quality.QHD: YTQuality.QHD_1440,
        Quality.UHD: YTQuality.UHD_2160,
    }
    quality_variants = [yt_addon.localize(str(yt_quality_map[q])) for q, _ in files]
    quality_idx = gui.select(yt_addon.localize('Select quality'), quality_variants)

    if quality_idx < 0:
        return None

    _, file = files[quality_idx]

    return file['url']


def catch_api_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        # if current_addon.debug:
        #     return func(*args, **kwargs)

        try:
            return func(*args, **kwargs)
        except boosty_api.BoostyApiError as err:
            error_message = str(err)
            alert(
                current_addon.localize('Boosty: Api Error'),
                err.response.json().get('error_description', error_message),
            )
        except boosty_api.BoostyError as err:
            error_message = str(err)
            alert(current_addon.localize('Boosty: Library Error'), error_message)

        current_addon.logger.error(error_message)
        xbmcplugin.endOfDirectory(current_addon.handle, False, False)
    return wrapper


def boosty_login(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        succeeded = True

        if current_addon.get_setting('boosty.enabled', bool):
            try:
                phone = current_addon.get_setting('boosty.phone')
                boosty_session.login = phone
                boosty_session.auth()
            except boosty_api.AuthError as err:
                alert(current_addon.localize('Boosty: Authentication Error'), str(err))
                succeeded = False

        if not succeeded:
            xbmcplugin.endOfDirectory(current_addon.handle, False, False)
        else:
            return func(*args, **kwargs)
    return wrapper


def download(username: str, post_id: str, media_idx: int) -> None:
    """Downloads a file from the Boosty server to the directory specified in the addon settings."""
    info = extract_info(username, post_id, media_idx)

    target_file = info['target_file']
    post = info['post']
    media = info['media']

    url = select_file_url(media['playerUrls'])

    if url is None:
        return None

    metadata = {
        'title': media['title'],
        'description': post.teaser.description,
        'date': post.publish_time.isoformat(),
        'artist': username,
    }

    downloader = YTDownloader(os.path.dirname(target_file))
    downloader.download(
        url,
        os.path.basename(target_file),
        quality=YTQuality.BEST,
        metadata=metadata,
        thumbnail=media['preview'],
        headers={
            'User-Agent': boosty_session.user_agent,
        },
    )


def extract_info(username: str, post_id: str, media_idx: int) -> t.Dict[str, t.Any]:
    post = boosty_session.get_post(username=username, post_id=post_id)
    media_files = post.get_media(boosty_api.MediaType.VIDEO)

    if len(media_files) < media_idx:
        raise boosty_api.BoostyError('File not found')

    media = media_files[media_idx]
    _, url = boosty_api.utils.select_best_quality(media['playerUrls'], skip_dash=True, skip_hls=True)

    output_dir = os.path.join(current_addon.get_setting('download_dir'), 'Boosty', username)
    title_prefix = f'{media_idx + 1:02}. ' if len(media_files) > 1 else ''
    filename = f"{username} - {post.publish_time:%Y_%m_%d} - {title_prefix}{post['title']}"

    downloader = YTDownloader(output_dir)

    info = downloader.extract_info(url, f'{filename}.%(ext)s', headers={
        'User-Agent': boosty_session.user_agent,
    })
    info['post'] = post
    info['media'] = media

    return info


def user_input_handler() -> int:
    code = prompt(current_addon.localize('Enter code from sms'), required=True, type_cast=int)

    if code:
        return code.value

    raise boosty_api.AuthError(
        current_addon.localize('You have cancelled the authentication.')
    )


def get_boosty_session() -> boosty_api.BoostyApi:
    return boosty_api.BoostyApi(
        credentials_filename=current_addon.get_data_path('boosty-credentials.json'),
        user_input_handler=user_input_handler,
        debug=current_addon.debug,
    )


boosty_session = get_boosty_session()
