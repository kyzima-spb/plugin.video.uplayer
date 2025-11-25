from collections import UserDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import cached_property, wraps
import re
from urllib.parse import urlparse, parse_qs
import typing as t

from kodi_useful import current_addon
from kodi_useful.exceptions import MultipleObjectsFound, ObjectNotFound
from kodi_useful.utils import get_screen_resolution
from requests import HTTPError

from ..parsers import make_session
from ..storage import ItemType
from ..utils import re_search


_T = t.TypeVar('_T')

YOUTUBE_BASE_URL = 'https://www.youtube.com'
YOUTUBE_MAX_RESULTS = 50


def adapter(url: str):
    result = urlparse(url)
    qs = {
        k: v if len(v) > 1 else v[0]
        for k, v in parse_qs(result.query).items()
    }

    if result.netloc not in ('www.youtube.com', 'youtu.be', 'youtube.com'):
        return None

    if result.path.startswith('/watch') or result.netloc == 'youtu.be':
        video_id = qs.get('v', re_search(r'/([^/]+)', result.path))
        obj = youtube_session.get_video_by_id(video_id)
        url = f'{YOUTUBE_BASE_URL}/watch?v={video_id}'
        item_type = ItemType.YOUTUBE_VIDEO
        is_folder = False
        data = {
            'video_id': video_id,
            'duration': obj.duration,
            'aired': obj.published.strftime('%Y-%m-%d %H:%M:%S'),
        }
    elif result.path.startswith('/playlist'):
        playlist_id = qs['list']
        obj = youtube_session.get_playlist_by_id(playlist_id)
        item_type = ItemType.YOUTUBE_PLAYLIST
        is_folder = True
        data = {
            'channel_id': obj.channel_id,
            'playlist_id': playlist_id,
        }
    else:
        item_type = ItemType.YOUTUBE_CHANNEL
        is_folder = True

        if result.path.startswith('/channel/'):
            channel_id = re_search(r'/channel/([^/]+)', result.path)
            obj = youtube_session.get_channel_by_id(channel_id)
        elif result.path.startswith('/@'):
            channel_handle = re_search(r'/(@[^/]+)', result.path)
            obj = youtube_session.get_channel_by_username(channel_handle)
        else:
            return None

        url = f'{YOUTUBE_BASE_URL}/channel/{obj["id"]}'
        data = {
            'channel_id': obj['id'],
            'upload_playlist_id': obj.upload_playlist_id,
        }

    thumbnail = youtube_session.http.download_file(obj.thumbnail) if obj.thumbnail else ''
    cover = youtube_session.http.download_file(obj.cover) if obj.cover else ''

    return {
        'url': url,
        'item_type': item_type,
        'is_folder': is_folder,
        'title': obj.title,
        'thumbnail': thumbnail,
        'cover': cover,
        'data': data,
    }


def catch_http_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except HTTPError as err:
            error_data = err.response.json()
            raise YouTubeApiError(**error_data['error']) from err
    return wrapper


@dataclass
class Collection(t.Generic[_T]):
    items: t.Sequence[_T]
    limit: int
    total: int
    next_page: str
    prev_page: str

    def __getitem__(self, key: int) -> _T:
        return self.items[key]

    def __iter__(self) -> t.Iterator[_T]:
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    @classmethod
    def from_response(cls, response_data, item_class: t.Optional[t.Type[_T]] = None):
        items = response_data['items']

        if item_class is not None:
            items = [item_class(**i) for i in items]

        return cls(
            items=items,
            next_page=response_data.get('nextPageToken'),
            prev_page=response_data.get('prevPageToken'),
            limit=response_data['pageInfo']['resultsPerPage'],
            total=response_data['pageInfo']['totalResults'],
        )


class SnippetMixin:
    @cached_property
    def description(self) -> str:
        snipped = self.data['snippet']
        return snipped.get('localized', snipped).get('description', '')

    @cached_property
    def published(self) -> datetime:
        return datetime.fromisoformat(self.data['snippet']['publishedAt'])

    @cached_property
    def title(self) -> str:
        snipped = self.data['snippet']
        return snipped.get('localized', snipped).get('title', '')


class ThumbnailMixin:
    def _get_thumbnail(self, size):
        thumbnails = sorted(self.data['snippet']['thumbnails'].items(), key=lambda p: p[1]['height'], reverse=True)

        for name, value in thumbnails:
            if size == name:
                return value['url']

        return ''

    @cached_property
    def cover(self) -> str:
        return self._get_thumbnail('maxres')

    @cached_property
    def thumbnail(self) -> str:
        return self._get_thumbnail('standard')


class Channel(SnippetMixin, ThumbnailMixin, UserDict):
    @cached_property
    def cover(self) -> str:
        branding_settings = self.data['brandingSettings']

        if 'image' not in branding_settings:
            return ''

        banner_url = branding_settings['image']['bannerExternalUrl']
        screen_width, screen_height = get_screen_resolution()

        return f'{banner_url}=s{screen_width}'

    @cached_property
    def thumbnail(self) -> str:
        return self._get_thumbnail('medium')

    @cached_property
    def upload_playlist_id(self) -> str:
        return self.data['contentDetails']['relatedPlaylists']['uploads']


class Playlist(SnippetMixin, ThumbnailMixin, UserDict):
    @cached_property
    def channel_id(self) -> str:
        return self.data['snippet']['channelId']


class Video(SnippetMixin, ThumbnailMixin, UserDict):
    @cached_property
    def duration(self) -> int:
        match = re.match(
            r'PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?',
            self.data['contentDetails']['duration']
        )

        if not match:
            return 0

        return timedelta(**{
            k: int(v) for k, v in match.groupdict().items() if v
        }).seconds


class YouTubeApiError(Exception):
    def __init__(self, code: int, message: str, status: str, errors: t.List[t.Dict[str, str]]) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.errors = errors


class YouTubeApi:
    def __init__(self, api_key: str = '') -> None:
        self._api_key = api_key

    @property
    def http(self):
        return make_session(
            base_url='https://youtube.googleapis.com/youtube/v3/',
            params={
                'key': self._api_key or current_addon.get_setting('youtube.apikey'),
            },
            headers={
                'Accept': 'application/json',
                'Accept-Language': 'ru-RU,ru;q=0.7',
                # 'Authorization': 'Bearer %s' % token,
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Content-Type': 'application/json',
            },
            cache={
                'ignored_parameters': ['key'],
            },
        )

    def _get_channel(self, **params) -> Channel:
        response_data = self._get_resource(
            '/channels', part='snippet,brandingSettings,contentDetails', **params,
        )
        return Channel(**response_data)

    @catch_http_error
    def _get_collection(
        self,
        path: str,
        page_token: str = '',
        limit: int = YOUTUBE_MAX_RESULTS,
        **params,
    ) -> t.Dict[str, t.Any]:
        params['maxResults'] = YOUTUBE_MAX_RESULTS if limit > YOUTUBE_MAX_RESULTS else limit
        params['pageToken'] = page_token
        return self.http.get(path, params=params).json()

    @catch_http_error
    def _get_resource(self, path: str, **params) -> t.Dict[str, t.Any]:
        response = self.http.get(path, params=params)
        response_data = response.json()

        if response_data['pageInfo']['totalResults'] == 1:
            return response_data['items'][0]

        if response_data['pageInfo']['totalResults'] > 1:
            raise MultipleObjectsFound(f'Multiple results found for: {response.url}.')

        raise ObjectNotFound(f'No result found: {response.url}.')

    def get_channel_by_id(self, channel_id: str) -> Channel:
        """Возвращает YouTube канал с указанным идентификатором."""
        return self._get_channel(id=channel_id)

    def get_channel_by_username(self, username: str) -> Channel:
        """Возвращает YouTube канал с указанным именем пользователя."""
        if username.startswith('@'):
            return self._get_channel(forHandle=username)
        return self._get_channel(forUsername=username)

    def get_playlist_by_id(self, playlist_id: str) -> Playlist:
        """Возвращает YouTube плейлист с указанным идентификатором."""
        response_data = self._get_resource('/playlists', id=playlist_id, part='snippet')
        return Playlist(**response_data)

    def get_playlists(
        self,
        channel_id: int,
        page_token: str = '',
        limit: int = YOUTUBE_MAX_RESULTS,
    ) -> Collection[Playlist]:
        """Возвращает YouTube плейлисты для указанного канала."""
        return Collection.from_response(
            self._get_collection(
                '/playlists', channelId=channel_id, part='snippet', page_token=page_token, limit=limit,
            ),
            item_class=Playlist,
        )

    def get_video_by_id(self, video_id) -> Video:
        """Возвращает YouTube видеозапись с указанным идентификатором."""
        response_data = self._get_resource('/videos', id=video_id, part='snippet,contentDetails')
        return Video(**response_data)

    def get_videos(
        self,
        playlist_id: str,
        page_token: str = '',
        limit: int = YOUTUBE_MAX_RESULTS,
    ) -> Collection[Video]:
        """Возвращает видеозаписи из YouTube плейлиста с указанным идентификатором."""
        playlist_items = self._get_collection(
            '/playlistItems', playlistId=playlist_id, part='contentDetails', limit=limit, page_token=page_token
        )
        videos = self._get_collection(
            '/videos',
            id=','.join(i['contentDetails']['videoId'] for i in playlist_items['items']),
            part='snippet,contentDetails',
        )
        playlist_items['items'] = videos['items']
        return Collection.from_response(playlist_items, item_class=Video)


youtube_session = YouTubeApi()
