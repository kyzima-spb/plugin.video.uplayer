import logging
import pathlib

import xbmcaddon
from xbmcvfs import translatePath


ADDON_PATH = pathlib.Path(translatePath(xbmcaddon.Addon().getAddonInfo('path')))
logging.basicConfig(
    filename=ADDON_PATH / 'log.txt',
    level=logging.DEBUG,
    format='{levelname}:{name}:{lineno}\n{message}\n',
    style='{',
)


get_logger = logging.getLogger
