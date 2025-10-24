import typing as t

from kodi_useful.http.client import Session


class MetaTagsCollection(tuple):
    def find(self, *keys, default=''):
        for name, value in self:
            if name in keys and value:
                return value
        return default


def make_session(base_url: t.Optional[str] = None, headers=None) -> Session:
    headers = headers or {}
    headers.setdefault('user-agent', 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0')
    return Session(base_url, headers=headers)


def parse_ogg_tags(url: str) -> MetaTagsCollection:
    root_elem = make_session().parse_html(url, allow_redirects=True)
    tags = [
        (elem.get('property'), elem.get('content'))
        for elem in root_elem.iterfind('.//head/meta')
        if elem.get('property')
    ]

    title_elem = root_elem.find('.//title')
    if title_elem is not None:
        tags.append(('title', title_elem.text))

    meta_description_elem = root_elem.find('.//meta[@name="description"]')
    if meta_description_elem is not None:
        tags.append(('description', meta_description_elem.get('content')))

    return MetaTagsCollection(tags)
