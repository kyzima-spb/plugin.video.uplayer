"""
https://rutube.ru/api/feeds/tnt/?format=api

# Проекты
# https://rutube.ru/api/metainfo/channel/23463954?client=wdp&limit=20&page=3
# limit - максимум 20
"""

from collections import UserDict
from functools import cached_property
import math
import typing as t
from types import SimpleNamespace

from kodi_useful.utils import get_screen_resolution
import m3u8

from ..parsers import make_session
from ..storage import ItemType
from ..utils import re_search


def adapter(url):
    if url.startswith('https://rutube.ru/video/'):
        video_id = re_search(r'/video/([^/]+)/', url)
        video = rutube_session.get_video_by_id(video_id)

        return {
            'item_type': ItemType.RUTUBE_VIDEO,
            'is_folder': False,
            'title': f'{video["author"]["name"]} - {video["title"]}',
            'description': video['description'],
            'thumbnail': video['thumbnail_url'],
            'cover': video['thumbnail_url'],
            'data': {
                'video_id': video['id'],
                'duration': math.ceil(video['duration'] / 1000),
            },
        }

    if url.startswith('https://rutube.ru/plst/'):
        playlist = rutube_session.get_playlist_by_id(get_playlist_id(url))
        return {
            'item_type': ItemType.RUTUBE_PLAYLIST,
            'is_folder': True,
            'title': f'{playlist["author"]["name"]} - {playlist["title"]}',
            'description': playlist['description'],
            'thumbnail': playlist['thumbnail_url'],
            'cover': playlist['thumbnail_url'],
            'data': {
                'playlist_id': playlist['id'],
            },
        }

    if url.startswith('https://rutube.ru/'):
        profile = rutube_session.get_user(get_channel_id(url))
        return {
            'item_type': ItemType.RUTUBE_CHANNEL,
            'is_folder': True,
            'title': profile['name'],
            'description': profile['description'],
            'thumbnail': profile['avatar_url'],
            'cover': profile['appearance'].get('cover_image'),
            'data': {
                'channel_id': profile['id'],
            },
        }


def get_channel_id(url: str) -> int:
    """Возвращает целочисленный идентификатор пользователя из URL адреса."""
    channel_id = (
        re_search(r'/channel/(\d+)', url)
        or
        re_search(r'"channel_id":.*?(\d+)', rutube_session.http.get(url).text)
    )

    if channel_id is None:
        raise ValueError(f'{url!r} is not Rutube channel.')

    return int(channel_id)


def get_playlist_id(url: str) -> int:
    """Возвращает целочисленный идентификатор плейлиста из URL адреса."""
    playlist_id = re_search(r'/plst/(\d+)', url)

    if playlist_id is None:
        raise ValueError(f'{url!r} is not Rutube playlist.')

    return int(playlist_id)


class Collection(SimpleNamespace):
    @cached_property
    def next_page(self) -> t.Optional[int]:
        if self.has_next:
            return self.page + 1

        if self.page > 1:
            return 1

        return None

    def __iter__(self):
        return iter(self.results)


class RutubeApi:
    def __init__(self) -> None:
        self.http = make_session(
            base_url='https://rutube.ru/api/',
            headers={
                'Accept-Language': 'ru-RU,ru;q=0.7',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Content-Type': 'application/json'
            }
        )
        self.http.params['client'] = 'wdp'

    def _get_collection(self, path: str, page: int = 1, **kwargs) -> Collection:
        response_data = self.http.get(path, params={'page': page, **kwargs}).json()
        return Collection(**response_data)

    def _get_resource(self, path: str, **kwargs) -> t.Dict[str, t.Any]:
        return self.http.get(path, **kwargs).json()

    def get_tv_channels(self, limit: int = 30, **kwargs) -> Collection:
        return self._get_collection('https://rutube.ru/api/video/topic/1/', limit=limit, **kwargs)

    def get_playlists(self, person_id: int, **kwargs) -> Collection:
        """Возвращает плейлисты для указанного пользователя."""
        return self._get_collection(
            '/playlist/user/{person_id}/',
            person_id=person_id,
            **kwargs,
        )

    def get_playlist_by_id(self, playlist_id: int) -> t.Dict[str, t.Any]:
        playlist = self._get_resource('/playlist/custom/{playlist_id}/', params={
            'playlist_id': playlist_id,
        })
        playlist['author'] = self.get_user(playlist['user_id'])
        return playlist

    def get_playlist_items(self, playlist_id: int, **kwargs) -> Collection:
        """Возвращает видео в указанном плейлисте."""
        return self._get_collection(
            '/playlist/custom/{playlist_id}/videos/',
            playlist_id=playlist_id,
            **kwargs,
        )

    def get_shorts(self, person_id: int, **kwargs) -> Collection:
        """Возвращает все короткие видео с канала указанного пользователя."""
        return self._get_collection(
            '/video/person/{person_id}/',
            person_id=person_id,
            origin__type='rshorts',
            **kwargs,
        )

    # def get_subscriptions(self) -> Collection:
    #     """Возвращает каналы, на которые подписан текущий пользователь."""
    #     return self._get_collection('/subscription/user/')

    def get_videos(self, person_id: int, **kwargs) -> Collection:
        """Возвращает все видео с канала указанного пользователя."""
        return self._get_collection(
            '/video/person/{person_id}/',
            person_id=person_id,
            **kwargs,
        )

    def get_video_by_id(self, video_id: str) -> 'Video':
        """Возвращает видео с указанным идентификатором."""
        return Video(**self._get_resource('/play/options/{video_id}', params={
            'video_id': video_id,
            '2k': 1,
            'av1': 1,
        }))

    def get_user(self, person_id: int) -> t.Dict[str, t.Any]:
        """Возвращает пользователя с указанным идентификатором."""
        return self._get_resource('/profile/user/{person_id}/', params={
            'person_id': person_id,
        })


class Video(UserDict):
    @cached_property
    def url(self) -> t.Optional[str]:
        if 'live_streams' in self.data:
            for stream_type, streams in self.data['live_streams'].items():
                for stream in streams:
                    if stream['is_video'] and stream['is_audio']:
                        return stream['url']

        if 'video_balancer' in self.data:
            return self.data['video_balancer'].get('m3u8', self.data['video_balancer']['default'])

        return None

    @cached_property
    def playlist(self) -> t.Optional[m3u8.model.M3U8]:
        if self.url is not None:
            return m3u8.load(self.url)

    @cached_property
    def best_quality_url(self) -> t.Optional[str]:
        if self.playlist is None:
            return None

        variants = sorted([
            v
            for v in self.playlist.playlists
            if v.stream_info.resolution <= get_screen_resolution()
        ], key=lambda v: v.stream_info.resolution, reverse=True)

        if not variants:
            variants = self.playlist.playlists

        return variants[0].uri


rutube_session = RutubeApi()
