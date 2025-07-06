from functools import lru_cache
from datetime import datetime
from dataclasses import dataclass, field, InitVar
import typing as t
from uuid import uuid4

from kodi_useful import current_addon
from kodi_useful.database import select, Connection, Model

from .parsers import parse_ogg_tags


SQL_SCHEMA = '''
    CREATE TABLE IF NOT EXISTS playlist (
        id VARCHAR(36) PRIMARY KEY,
        title TEXT NOT NULL,
        ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS playlist_item (
        id VARCHAR(36) PRIMARY KEY,
        playlist_id VARCHAR(36),
        url TEXT NOT NULL,
        title TEXT NOT NULL,
        ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (playlist_id)
            REFERENCES playlist(id)
                ON UPDATE CASCADE
                ON DELETE CASCADE
    );
'''


def pk():
    return str(uuid4())


# @lru_cache
def get_connection() -> Connection:
    db_path = current_addon.get_data_path('player.db')
    current_addon.logger.debug(db_path)

    conn = Connection(db_path)
    conn.executescript(SQL_SCHEMA)

    return conn


@dataclass(eq=False)
class BaseModel(Model):
    @classmethod
    def get_connection(cls) -> Connection:
        return get_connection()


@dataclass(eq=False)
class Playlist(BaseModel):
    title: str
    id: str = field(default_factory=pk)
    ts: datetime = field(default_factory=lambda: datetime.utcnow())

    @classmethod
    def select(cls, limit: int, offset: int) -> t.Sequence['Playlist']:
        stmt = (
            select(cls)
            .order_by('ts', desc=True)
            .limit(limit)
            .offset(offset)
        )
        return cls.get_connection().query(stmt).fetchall()


@dataclass(eq=False)
class PlaylistItem(BaseModel):
    url: str
    title: str = ''
    id: str = field(default_factory=pk)
    ts: str = field(default_factory=lambda: datetime.utcnow())
    playlist_id: t.Optional[str] = None

    def __post_init__(self) -> None:
        if not self.title:
            self.update_url(self.url)

    def update_url(self, url):
        meta_tags = parse_ogg_tags(url)
        self.url = url
        self.title = meta_tags.find('og:title', 'twitter:title', default=url)

    @classmethod
    def select(
        cls,
        limit: int,
        offset: int,
        playlist_id: t.Optional[str] = None,
    ) -> t.Sequence['PlaylistItem']:
        stmt = select(cls)
        parameters = {}

        if playlist_id is None:
            stmt = ' WHERE playlist_id IS NULL'
        else:
            stmt += ' WHERE playlist_id = :playlist_id'
            parameters['playlist_id'] = playlist_id

        stmt = stmt.order_by('ts', desc=True).limit(limit).offset(offset)

        return cls.get_connection().query(stmt, parameters).fetchall()
