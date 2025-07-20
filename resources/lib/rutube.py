"""
Мои подписки
https://rutube.ru/api/subscription/user/
https://rutube.ru/api/subscription/user/?client=wdp

https://rutube.ru/api/feeds/tnt/?format=api
https://rutube.ru/api/playlist/custom/53542/videos/?page=2&client=wdp
https://rutube.ru/api/video/person/31303018/?client=wdp&origin__type=rtb%2Crst%2Cifrm%2Crspa&page=2

https://rutube.ru/api/playlist/custom/361027/
https://rutube.ru/api/playlist/custom/361027/videos/?page=2&client=wdp
https://rutube.ru/api/playlist/user/25390625
"""

import re
import string
from types import SimpleNamespace

from kodi_useful import current_addon
from kodi_useful.http.client import Session


session = Session(
    base_url='https://rutube.ru/api/',
    headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'Accept-Language': 'ru-RU,ru;q=0.7',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Content-Type': 'application/json'
    }
)


def get_channel_id(url: str) -> int:
    """Возвращает целочисленный идентификатор пользователя из URL адреса."""
    match = re.search(r'/channel/(\d+)', url)

    if match:
        return int(match.group(1))

    match = re.search(r'"channel_id":.*?(\d+)', session.get(url).text)

    if match:
        return int(match.group(1))

    raise ValueError(f'{url!r} is not Rutube channel.')


def get_playlist_id(url: str) -> int:
    """Возвращает целочисленный идентификатор плейлиста из URL адреса."""
    match = re.search(r'/plst/(\d+)/', url)

    if match:
        return int(match.group(1))

    raise ValueError(f'{url!r} is not Rutube playlist.')


class Model(SimpleNamespace):
    pass


class Collection(SimpleNamespace):
    _obj_cls = Model
    _path: str = ''

    @classmethod
    def list(cls, page: int = 1, **kwargs):
        formatter = string.Formatter()

        url = cls._path.format(**{
            field_name: kwargs.pop(field_name)
            for _, field_name, _, _ in formatter.parse(cls._path)
            if field_name
        })
        params = {'page': page, **kwargs}

        response = session.get(url, params=params)
        response.raise_for_status()

        return cls(**response.json())

    def __iter__(self):
        # current_addon.logger.debug(self)
        return (self._obj_cls(**i) for i in self.results)


class Playlists(Collection):
    _path = '/playlist/user/{person_id}/'


class PlaylistItems(Collection):
    _path = '/playlist/custom/{playlist_id}/videos/'


class Videos(Collection):
    _path = '/video/person/{person_id}/'


class Shorts(Collection):
    _path = '/video/person/{person_id}/?client=wdp&origin__type=rshorts'


# Проекты
# https://rutube.ru/api/metainfo/channel/23463954?client=wdp&limit=20&page=3

# limit - максимум 20
