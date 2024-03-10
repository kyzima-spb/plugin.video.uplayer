from __future__ import annotations
from dataclasses import dataclass, field
from functools import wraps
import logging
import pathlib
import sqlite3
import typing as t
from uuid import uuid4

import xbmcaddon
from xbmcvfs import translatePath


_F = t.TypeVar('_F', bound=t.Callable[..., t.Any])

logger = logging.getLogger(__name__)

SQL_SCHEMA = '''
    CREATE TABLE IF NOT EXISTS playlist (
        id VARCHAR(36) PRIMARY KEY,
        label TEXT NOT NULL
    );
    
    CREATE TABLE IF NOT EXISTS playlist_item (
        id VARCHAR(36) PRIMARY KEY,
        playlist_id VARCHAR(36),
        url TEXT NOT NULL,
        label TEXT NOT NULL,
        FOREIGN KEY (playlist_id)
            REFERENCES playlist(id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
    );
'''


def pk():
    return str(uuid4())


def with_connection(func: _F) -> _F:
    @wraps(func)
    def wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
        profile_path = translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
        db_path = pathlib.Path(profile_path) / 'playlist.db'
        is_fresh_instance = not db_path.exists()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        conn.set_trace_callback(logger.debug)
        conn.execute('PRAGMA foreign_keys = ON')

        if is_fresh_instance:
            with conn:
                conn.executescript(SQL_SCHEMA)

        with conn:
            return func(*args, **kwargs, conn=conn)

    return wrapper


@dataclass
class Playlist:
    _count_stmt = 'SELECT count(*) FROM playlist'
    _delete_stmt = 'DELETE FROM playlist WHERE id=?'
    _insert_stmt = 'INSERT INTO playlist (label, id) VALUES (?, ?)'
    _select_stmt = 'SELECT id, label FROM playlist'
    _select_by_pk_stmt = '%s WHERE id=?' % _select_stmt
    _select_with_paginate_stmt = '%s LIMIT ? OFFSET ?' % _select_stmt
    _update_stmt = 'UPDATE playlist SET label=? WHERE id=?'

    label: str
    id: str = field(default_factory=pk)

    @classmethod
    @with_connection
    def count(cls, conn) -> int:
        return conn.execute(cls._count_stmt).fetchone()[0]

    @with_connection
    def delete(self, conn) -> None:
        conn.execute(self._delete_stmt, (self.id,))

    @classmethod
    @with_connection
    def get(cls, conn, playlist_id) -> Playlist:
        row = conn.execute(cls._select_by_pk_stmt, (playlist_id,)).fetchone()
        if row is None:
            raise ValueError('Playlist not found')
        return cls(**row)

    @with_connection
    def save(self, conn) -> None:
        conn.execute(self._insert_stmt, (self.label, self.id))

    @classmethod
    @with_connection
    def select(cls, conn, limit=12, offset=0) -> t.List[Playlist]:
        r = conn.execute(cls._select_with_paginate_stmt, (limit, offset))
        return [cls(**i) for i in r]

    @with_connection
    def update(self, conn) -> None:
        conn.execute(self._update_stmt, (self.label, self.id))


@dataclass
class PlaylistItem:
    _delete_stmt = 'DELETE FROM playlist_item WHERE id=?'
    _insert_stmt = '''
        INSERT INTO playlist_item (
            id, url, label, playlist_id
        ) VALUES (
            ?, ?, ?, ?
        )
    '''
    _select_stmt = '''
        SELECT
            id, playlist_id, url, label
        FROM
            playlist_item
    '''
    _select_by_pk_stmt = '%s WHERE id=?' % _select_stmt

    url: str
    label: str
    id: str = field(default_factory=pk)
    playlist_id: t.Optional[str] = None

    @with_connection
    def delete(self, conn) -> None:
        conn.execute(self._delete_stmt, (self.id,))

    @classmethod
    @with_connection
    def get(cls, conn, item_id) -> PlaylistItem:
        row = conn.execute(cls._select_by_pk_stmt, (item_id,)).fetchone()
        if row is None:
            raise ValueError('Playlist item not found')
        return cls(**row)

    @with_connection
    def save(self, conn) -> None:
        conn.execute(self._insert_stmt, (
            self.id, self.url, self.label, self.playlist_id,
        ))

    @classmethod
    @with_connection
    def select(cls, conn, playlist_id=None, limit=12, offset=0) -> t.List[PlaylistItem]:
        if playlist_id is None:
            stmt = '%s WHERE playlist_id IS NULL LIMIT ? OFFSET ?' % cls._select_stmt
            r = conn.execute(stmt, (limit, offset))
        else:
            stmt = '%s WHERE playlist_id=? LIMIT ? OFFSET ?' % cls._select_stmt
            r = conn.execute(stmt, (playlist_id, limit, offset))
        return [cls(**i) for i in r]

    @classmethod
    @with_connection
    def count(cls, conn, playlist_id=None) -> int:
        if playlist_id is None:
            stmt = 'SELECT count(*) FROM playlist_item WHERE playlist_id IS NULL'
            r = conn.execute(stmt)
        else:
            stmt = 'SELECT count(*) FROM playlist_item WHERE playlist_id=?'
            r = conn.execute(stmt, (playlist_id,))
        return r.fetchone()[0]
