import typing as t

from ..parsers import parse_ogg_tags
from ..storage import Item, ItemType


class MediaProvider:
    def __init__(self):
        self._adapters = []

    def get_data(self, title_or_url: str) -> t.Dict[str, t.Any]:
        if not title_or_url.startswith('http://') and not title_or_url.startswith('https://'):
            return {
                'item_type': ItemType.FOLDER,
                'is_folder': True,
                'title': title_or_url,
            }

        url = title_or_url
        meta = parse_ogg_tags(url)

        for adapter in self._adapters:
            data = adapter(url)

            if data is not None:
                data['title'] = data.get('title') or meta.find('og:title', 'twitter:title', 'title', default=url)
                data['description'] = data.get('description') or meta.find('og:description', 'twitter:description')
                data['url'] = data.get('url') or url
                data['thumbnail'] = data.get('thumbnail') or meta.find('og:image', 'twitter:image')
                return data
        else:
            return {
                'item_type': ItemType.VIDEO,
                'is_folder': False,
                'title': meta.find('og:title', 'twitter:title', 'title', default=url),
                'description': meta.find('og:description', 'twitter:description'),
                'url': url,
                'thumbnail': meta.find('og:image', 'twitter:image'),
                'cover': meta.find('og:image', 'twitter:image'),
            }

    def create_item(self, title_or_url: str, parent_id: t.Optional[int] = None) -> Item:
        data = self.get_data(title_or_url)
        return Item(parent_id=parent_id, **data)

    def register_adapter(self, adapter):
        self._adapters.append(adapter)
        return adapter
