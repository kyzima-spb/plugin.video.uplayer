from htmlement import HTMLement
import requests

from kodi_useful.exceptions import ValidationError


class MetaTagsCollection(tuple):
    def find(self, *keys, default=None):
        for name, value in self:
            if name in keys and value:
                return value
        return default


def parse_ogg_tags(url):
    resp = requests.get(url, allow_redirects=True, headers={
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
    })

    try:
        resp.raise_for_status()
    except requests.HTTPError as err:
        raise ValidationError('%s for url: %s' % (resp.reason, resp.url)) from err

    parser = HTMLement()
    parser.feed(resp.text)
    root_elem = parser.close()

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


if __name__ == '__main__':
    urls = [
        # 'https://vk.com/video190953452_456239269',
        # 'https://rutube.ru/video/d9a5422c038967103dd5034273edcc1c',
        'https://www.youtube.com/watch?v=7vjggerkZ8E',
        # 'https://dzen.ru/video/watch/6068ac374e1bd509492781eb',
        # 'http://blog.mail.ru/kyzima-spb',
        # 'http://old-dos.ru',
        # 'https://docs.python.org/3/library/dataclasses.html#dataclasses.__post_init__',
    ]
    for url in urls:
        meta_tags = parse_ogg_tags(url)
        print(meta_tags)
        # props = {
        #     'title': ('og:title', 'twitter:title'),
        #     'url': ('og:url', 'twitter:url'),
        #     'description': ('og:description', 'twitter:description'),
        #     'image': ('og:image', 'twitter:image'),
        #     'duration': ('og:video:duration',),
        #     'width': ('og:video:width',),
        #     'height': ('og:video:height',),
        #     'date': ('og:video:release_date',),
        # }

    # meta = parse_ogg_tags('https://vk.com/video_ext.php?oid=190953452&id=456239269')
