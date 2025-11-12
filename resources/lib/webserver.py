from functools import wraps
from http import HTTPStatus

from kodi_useful import current_addon
from kodi_useful.http.server import HTTPServer, HTTPRequestHandler

from .storage import Item
from .providers import media_provider


httpd = HTTPServer()


def catch_exception(func):
    @wraps(func)
    def wrapper(rh: HTTPRequestHandler, *args, **kwargs):
        try:
            return func(rh, *args, **kwargs)
        except Exception as err:
            return rh.send_json(str(err), HTTPStatus.INTERNAL_SERVER_ERROR)
    return wrapper


@httpd.get('/')
def index(request_handler: HTTPRequestHandler):
    return request_handler.render_template('index.html')


@httpd.get('/items')
@catch_exception
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
@catch_exception
def create_item(rh: HTTPRequestHandler):
    playlist = media_provider.create_item(
        title_or_url=rh.form.get('title', required=True),
        parent_id=rh.query.get('folder_id'),
    )
    playlist.save()
    return rh.send_json(playlist.as_dict())


@httpd.delete('/items')
@catch_exception
def delete_item(rh: HTTPRequestHandler):
    item_id = rh.query.get('item_id', required=True)
    Item.find(item_id).delete()
    return HTTPStatus.NO_CONTENT


@httpd.put('/items')
@catch_exception
def edit_item(rh: HTTPRequestHandler):
    item_id = rh.query.get('item_id', required=True)

    item = Item.find(item_id)
    item.title = rh.form.get('title', required=True)
    item.save()

    return rh.send_json(item.as_dict())
