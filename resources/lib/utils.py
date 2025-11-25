import re
import typing as t

from kodi_useful import current_addon


def get_icon(name: str) -> str:
    return current_addon.get_path('resources', 'lib', 'assets', 'icons', name)


def re_search(pattern: str, s: str) -> t.Optional[str]:
    match = re.search(pattern, s)
    return match.group(1) if match else None


class URLConstructor:
    def __init__(self):
        self._map = {}

    def __call__(self, type_name: str, *args, **kwargs):
        if type_name not in self._map:
            raise ValueError(f'URL constructor not found: unknown type {type_name!r}')
        return self._map[type_name](*args, **kwargs)

    def register(self, type_name: str):
        def decorator(func):
            self._map[type_name] = func
            return func
        return decorator
