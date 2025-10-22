from .base import MediaProvider
from .boosty import adapter as boosty_adapter
from .rutube import adapter as rutube_adapter


media_provider = MediaProvider()
media_provider.register_adapter(boosty_adapter)
media_provider.register_adapter(rutube_adapter)
