from http import HTTPStatus

from kodi_useful import current_addon
from kodi_useful.http.server import HTTPServer, HTTPRequestHandler

from .storage import Playlist, PlaylistItem
from .providers import media_provider


httpd = HTTPServer()


@httpd.get('/')
def index(request_handler: HTTPRequestHandler):
    return request_handler.render_template('index.html')


@httpd.get('/playlists')
def list_playlists(rh: HTTPRequestHandler):
    playlists = Playlist.select(
        limit=rh.query.get_int(
            'limit', default=current_addon.get_setting('items_per_page', int)
        ),
        offset=rh.query.get_int('offset', default=0),
    )
    return rh.send_json([p.as_dict() for p in playlists])


@httpd.post('/playlists')
def create_playlist(rh: HTTPRequestHandler):
    playlist = media_provider.create_model(
        rh.form.get('title', required=True),
        model_class=Playlist,
    )
    playlist.save()
    return rh.send_json(playlist.as_dict())


@httpd.delete('/playlists')
def delete_playlist(rh: HTTPRequestHandler):
    playlist_id = rh.query.get('playlist_id', required=True)
    Playlist.find(playlist_id).delete()
    return HTTPStatus.NO_CONTENT


@httpd.put('/playlists')
def edit_playlist(rh: HTTPRequestHandler):
    playlist_id = rh.query.get('playlist_id', required=True)

    playlist = Playlist.find(playlist_id)
    playlist.title = rh.form.get('title', required=True)
    playlist.save()

    return rh.send_json(playlist.as_dict())


@httpd.get('/items')
def list_playlist_items(rh: HTTPRequestHandler):
    playlist_id = rh.query.get('playlist_id')
    playlist = None

    if playlist_id:
        playlist = Playlist.find(playlist_id)

    playlist_items = PlaylistItem.select(
        playlist_id=playlist_id,
        offset=rh.query.get_int('offset', default=0),
        limit=rh.query.get_int(
            'limit', default=current_addon.get_setting('items_per_page', int)
        ),
    )

    return rh.send_json({
        'playlist': None if playlist is None else playlist.as_dict(),
        'items': [i.as_dict() for i in playlist_items],
    })


@httpd.post('/items')
def create_playlist_item(rh: HTTPRequestHandler):
    playlist_item = PlaylistItem(
        url=rh.form.get('url', required=True),
        playlist_id=rh.query.get('playlist_id'),
    )
    playlist_item.save()
    return rh.send_json(playlist_item.as_dict())


@httpd.delete('/items')
def delete_playlist_item(rh: HTTPRequestHandler):
    item_id = rh.query.get('item_id', required=True)
    PlaylistItem.find(item_id).delete()
    return HTTPStatus.NO_CONTENT


@httpd.put('/items')
def edit_playlist_item(rh: HTTPRequestHandler):
    item_id = rh.query.get('item_id', required=True)

    playlist_item = PlaylistItem.find(item_id)
    playlist_item.update_url(rh.form.get('url', required=True))
    playlist_item.save()

    return rh.send_json(playlist_item.as_dict())
