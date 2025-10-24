import typing as t

from ..parsers import parse_ogg_tags
from ..storage import PlaylistType, Playlist


class MediaProvider:
    def __init__(self):
        self._adapters = []

    def get_data(self, title_or_url: str) -> t.Dict[str, t.Any]:
        if not title_or_url.startswith('http://') and not title_or_url.startswith('https://'):
            return {'type_name': PlaylistType.MANUAL, 'title': title_or_url}

        url = title_or_url
        meta = parse_ogg_tags(url)

        for adapter in self._adapters:
            data = adapter(url)

            if data is not None:
                data['title'] = data.get('title') or meta.find('og:title', 'twitter:title', 'title', default=url)
                data['description'] = data.get('description') or meta.find('og:description', 'twitter:description')
                data['cover'] = data.get('cover') or meta.find('og:image', 'twitter:image')
                data.setdefault('data', {}).setdefault('url', url)
                return data
        else:
            raise ValueError(f'Unknown URL: {url!r}')

    def create_model(self, title_or_url: str, model_class=t.Type[Playlist]) -> Playlist:
        data = self.get_data(title_or_url)
        return model_class(**data)

    def register_adapter(self, adapter):
        self._adapters.append(adapter)
        return adapter
