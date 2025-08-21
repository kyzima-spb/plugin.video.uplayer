from datetime import datetime
from dataclasses import dataclass, field
import enum
import typing as t
from uuid import uuid4

from boosty_api.utils import extract_text as boosty_extract_text
from kodi_useful import current_addon
from kodi_useful.database import select, Connection, Model

from .services import boosty
from . import rutube
from .parsers import parse_ogg_tags


SQL_SCHEMA = '''
    CREATE TABLE IF NOT EXISTS playlist_type (
        name VARCHAR(16) PRIMARY KEY    
    );
    
    INSERT INTO playlist_type VALUES
        ('boosty'),
        ('manual'),
        ('rutube_channel'),
        ('rutube_playlist'),
        ('vk'),
        ('youtube_channel')
    ON CONFLICT(name) DO NOTHING;
    
    CREATE TABLE IF NOT EXISTS playlist (
        id VARCHAR(36) PRIMARY KEY,
        type_name VARCHAR(16) NOT NULL DEFAULT 'manual',
        title TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        cover VARCHAR(255) NOT NULL DEFAULT '',
        data JSON NOT NULL DEFAULT '{}',
        ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(type_name)
            REFERENCES playlist_type(name)
                ON UPDATE CASCADE
                ON DELETE SET DEFAULT
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
    
    CREATE TABLE IF NOT EXISTS saved_file (
        id INTEGER PRIMARY KEY,
        service VARCHAR(16) NOT NULL,
        media_id TEXT NOT NULL,
        file TEXT NOT NULL,
        title TEXT NULL DEFAULT '',
        description TEXT NULL DEFAULT '', 
        cover TEXT NOT NULL DEFAULT '',
        duration INTEGER NOT NULL DEFAULT 0
    );
'''


class PlaylistType(enum.StrEnum):
    BOOSTY = enum.auto()
    MANUAL = enum.auto()
    RUTUBE_CHANNEL = enum.auto()
    RUTUBE_PLAYLIST = enum.auto()
    VK = enum.auto()
    YOUTUBE = enum.auto()


def pk():
    return str(uuid4())


# @lru_cache
def get_connection() -> Connection:
    db_path = current_addon.get_data_path('player.db')
    current_addon.logger.debug(db_path)

    conn = Connection(db_path, echo=True)
    conn.executescript(SQL_SCHEMA, raw=True)

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
    type_name: PlaylistType = field(default=PlaylistType.MANUAL)
    description: str = ''
    cover: str = ''
    data: t.Dict[str, t.Any] = field(default_factory=dict)
    ts: datetime = field(default_factory=lambda: datetime.utcnow())

    @classmethod
    def create(cls, title_or_url: str) -> 'Playlist':
        type_name = PlaylistType.MANUAL

        if not title_or_url.startswith('http://') and not title_or_url.startswith('https://'):
            return cls(type_name=type_name, title=title_or_url)

        url = title_or_url
        meta_tags = parse_ogg_tags(url)
        data = {
            'url': url,
        }

        title = meta_tags.find('og:title', 'twitter:title', 'title', default=title_or_url)
        description = meta_tags.find('og:description', 'twitter:description', default='')
        cover = meta_tags.find('og:image', 'twitter:image', default='')

        if url.startswith('https://rutube.ru/plst'):
            type_name = PlaylistType.RUTUBE_PLAYLIST
            data['playlist_id'] = rutube.get_playlist_id(url)
        elif url.startswith('https://rutube.ru/'):
            type_name = PlaylistType.RUTUBE_CHANNEL
            data['channel_id'] = rutube.get_channel_id(url)
        elif url.startswith('https://boosty.to/'):
            user = boosty.boosty_session.get_profile_by_url(url)
            type_name = PlaylistType.BOOSTY
            title = f"{user['owner']['name']} - {user['title']}"
            description = boosty_extract_text(user['description'])
            cover = user['owner']['avatarUrl']
            data['username'] = user['blogUrl']
            data['url'] = f"https://boosty.to/{user['blogUrl']}/"
        else:
            raise ValueError(f'Unknown URL: {url}.')

        return cls(type_name=type_name, title=title, description=description, cover=cover, data=data)

    @classmethod
    def select(cls, limit: int, offset: int) -> t.Sequence['Playlist']:
        stmt = (
            select(cls)
            .order_by('title')
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
            stmt += ' WHERE playlist_id IS NULL'
        else:
            stmt += ' WHERE playlist_id = :playlist_id'
            parameters['playlist_id'] = playlist_id

        stmt = stmt.order_by('ts', desc=True).limit(limit).offset(offset)

        return cls.get_connection().query(stmt, parameters).fetchall()
