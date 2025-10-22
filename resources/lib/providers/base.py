import typing as t

from ..parsers import parse_ogg_tags
from ..storage import PlaylistType, Playlist


class MediaProvider:
    def __init__(self):
        self._adapters = set()

    def create_model(self, title_or_url: str, model_class=t.Type[Playlist]) -> Playlist:
        if not title_or_url.startswith('http://') and not title_or_url.startswith('https://'):
            return model_class(type_name=PlaylistType.MANUAL, title=title_or_url)

        url = title_or_url
        meta_tags = parse_ogg_tags(url)
        data = {
            'url': url,
        }

        for adapter in self._adapters:
            user_data = adapter(url)

            if user_data is not None:
                data.update(user_data)
                break
        else:
            raise ValueError(f'Unknown URL: {url!r}')

        type_name = data.pop('type_name', PlaylistType.MANUAL)
        title = meta_tags.find('og:title', 'twitter:title', 'title', default=data.pop('title', url))
        description = meta_tags.find('og:description', 'twitter:description', default=data.pop('description', ''))
        cover = meta_tags.find('og:image', 'twitter:image', default=data.pop('cover', ''))

        return model_class(type_name=type_name, title=title, description=description, cover=cover, data=data)

    def register_adapter(self, adapter):
        self._adapters.add(adapter)
        return adapter
