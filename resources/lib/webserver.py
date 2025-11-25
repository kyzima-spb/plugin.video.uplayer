from dataclasses import asdict, dataclass, fields
from functools import wraps
from http import HTTPStatus
import typing as t

from kodi_useful import current_addon
from kodi_useful.exceptions import HTTPError
from kodi_useful.http.server import validate, HTTPServer, HTTPRequestHandler

from .storage import Item
from .providers import media_provider


def required_security_page(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_addon.get_setting('httpd.security', bool):
            raise HTTPError(HTTPStatus.FORBIDDEN, 'You need to enable the security page in the addon settings.')
        return func(*args, **kwargs)
    return wrapper


@dataclass
class SecuritySettings:
    youtube_apikey: str = ''
    youtube_client_id: str = ''
    youtube_secret_key: str = ''

    def as_dict(self) -> t.Dict[str, t.Any]:
        return asdict(self)

    @classmethod
    def load(cls) -> 'SecuritySettings':
        return cls(**{
            f.name: current_addon.get_setting(f.name.replace('_', '.'), f.type)
            for f in fields(cls)
        })

    def save(self) -> None:
        for f in fields(self):
            current_addon.set_setting(f.name.replace('_', '.'), getattr(self, f.name))

    @classmethod
    def validate(cls, payload) -> 'SecuritySettings':
        return validate(cls, payload)


httpd = HTTPServer()


@httpd.get('/')
def index(request_handler: HTTPRequestHandler):
    return request_handler.render_template('index.html')


@httpd.get('/items')
def list_items(rh: HTTPRequestHandler):
    items = Item.select(
        parent_id=rh.query.get_int('folder_id'),
        limit=rh.query.get_int(
            'limit', default=current_addon.get_setting('items_per_page', int)
        ),
        offset=rh.query.get_int('offset', default=0),
    )
    return rh.send_json([i.as_dict() for i in items])


@httpd.post('/items')
def create_item(rh: HTTPRequestHandler):
    playlist = media_provider.create_item(
        title_or_url=rh.form.get('title', required=True),
        parent_id=rh.query.get('folder_id'),
    )
    playlist.save()
    return rh.send_json(playlist.as_dict())


@httpd.delete('/items')
def delete_item(rh: HTTPRequestHandler):
    item_id = rh.query.get('item_id', required=True)
    Item.find(item_id).delete()
    return HTTPStatus.NO_CONTENT


@httpd.put('/items')
def edit_item(rh: HTTPRequestHandler):
    item_id = rh.query.get('item_id', required=True)

    item = Item.find(item_id)
    item.title = rh.form.get('title', required=True)
    item.save()

    return rh.send_json(item.as_dict())


@httpd.get('/security')
@required_security_page
def get_security_settings(rh: HTTPRequestHandler):
    return rh.send_json(SecuritySettings.load().as_dict())


@httpd.put('/security')
@required_security_page
def update_security_settings(rh: HTTPRequestHandler):
    settings = SecuritySettings.validate(rh.json)
    settings.save()
    return rh.send_json(settings.as_dict())
