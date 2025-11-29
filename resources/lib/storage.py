from datetime import datetime
from dataclasses import dataclass, field
import enum
import typing as t

from kodi_useful import current_addon
from kodi_useful.database import select, Connection, Model


SQL_SCHEMA = '''
    CREATE TABLE IF NOT EXISTS item_type (
        name VARCHAR(16) PRIMARY KEY    
    );
    
    INSERT INTO item_type VALUES
        ('boosty_profile'),
        ('boosty_post'),
        ('boosty_video'),
        ('folder'),
        ('rutube_channel'),
        ('rutube_playlist'),
        ('rutube_video'),
        ('video'),
        ('youtube_channel'),
        ('youtube_playlist'),
        ('youtube_video')
    ON CONFLICT(name) DO NOTHING;
    
    CREATE TABLE IF NOT EXISTS item (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        parent_id INTEGER,
        item_type VARCHAR(16) NOT NULL,
        is_folder BOOLEAN NOT NULL DEFAULT 0,
        title TEXT NOT NULL,
        description TEXT NOT NULL DEFAULT '',
        url TEXT NOT NULL DEFAULT '',
        thumbnail VARCHAR(255) NOT NULL DEFAULT '',
        cover VARCHAR(255) NOT NULL DEFAULT '',
        data JSON NOT NULL DEFAULT '{}',
        ts DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(parent_id)
            REFERENCES item(id)
                ON UPDATE CASCADE
                ON DELETE CASCADE,
        FOREIGN KEY(item_type)
            REFERENCES item_type(name)
                ON UPDATE CASCADE
                ON DELETE SET DEFAULT
    );
    
    CREATE TABLE IF NOT EXISTS saved_file (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service VARCHAR(16) NOT NULL,
        media_id TEXT NOT NULL,
        file TEXT NOT NULL,
        title TEXT NULL DEFAULT '',
        description TEXT NULL DEFAULT '', 
        cover TEXT NOT NULL DEFAULT '',
        duration INTEGER NOT NULL DEFAULT 0
    );
'''


class ItemType(enum.StrEnum):
    BOOSTY_PROFILE = enum.auto()
    BOOSTY_POST = enum.auto()
    BOOSTY_VIDEO = enum.auto()
    CTC = enum.auto()
    FOLDER = enum.auto()
    RUTUBE_CHANNEL = enum.auto()
    RUTUBE_PLAYLIST = enum.auto()
    RUTUBE_VIDEO = enum.auto()
    VIDEO = enum.auto()
    VK = enum.auto()
    YOUTUBE_CHANNEL = enum.auto()
    YOUTUBE_PLAYLIST = enum.auto()
    YOUTUBE_VIDEO = enum.auto()


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
class Item(BaseModel):
    item_type: ItemType
    is_folder: bool
    title: str
    id: t.Optional[int] = None
    parent_id: t.Optional[int] = None
    description: str = ''
    url: str = ''
    thumbnail: str = ''
    cover: str = ''
    data: t.Dict[str, t.Any] = field(default_factory=dict)
    ts: datetime = field(default_factory=datetime.utcnow)

    @property
    def provider(self) -> str:
        return ItemType(self.item_type).value.split('_')[0]

    @classmethod
    def select(cls, parent_id: t.Optional[int], limit: int, offset: int) -> t.Sequence['Item']:
        stmt = select(cls)
        parameters = {}

        if parent_id is None:
            stmt += ' WHERE parent_id IS NULL'
        else:
            stmt += ' WHERE parent_id = :parent_id'
            parameters['parent_id'] = parent_id

        stmt += '''
        ORDER BY
            is_folder DESC,
            CASE WHEN is_folder = 1 THEN title END ASC,
            CASE WHEN is_folder = 0 THEN ts END DESC
        '''

        return cls.get_connection().query(
            stmt.limit(limit).offset(offset), parameters,
        ).fetchall()


# @dataclass(eq=False)
# class Item(BaseModel):
#     url: str
#     title: str = ''
#     id: t.Optional[int] = None
#     folder_id: t.Optional[int] = None
#     ts: str = field(default_factory=datetime.utcnow)
#
#     def __post_init__(self) -> None:
#         if not self.title:
#             self.update_url(self.url)
#
#     def update_url(self, url):
#         meta_tags = parse_ogg_tags(url)
#         self.url = url
#         self.title = meta_tags.find('og:title', 'twitter:title', default=url)
