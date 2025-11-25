import typing as t

from kodi_useful import (
    create_next_element,
    current_addon,
    router,
    Addon,
    Directory,
)
from kodi_useful.gui import alert, prompt
from kodi_useful.enums import Content, Scope
from kodi_useful.utils import open_browser
import xbmc
import xbmcgui
import xbmcplugin

from ..storage import Item, ItemType
from ..providers import media_provider
from ..utils import URLConstructor


url_construct = URLConstructor()


@url_construct.register(ItemType.FOLDER)
def get_url_for_folder_item(folder: Item) -> str:
    """Возвращает ссылку для отображения элементов директории."""
    return current_addon.url_for(list_items, folder_id=folder.id, title=folder.title)


@url_construct.register(ItemType.VIDEO)
def get_url_for_video_item(item: Item) -> str:
    """Возвращает ссылку для воспроизведения видеозаписи."""
    return current_addon.url_for(play_video, url=item.url)


@router.route
def play_video(addon: Addon, url: t.Annotated[str, Scope.QUERY]) -> None:
    open_browser(url)
    xbmcplugin.setResolvedUrl(addon.handle, True, xbmcgui.ListItem())


@router.route(is_root=True)
@Directory(
    ltitle='',
    content=Content.VIDEOS,
    cache_to_disk=True,
)
def list_items(
    addon: Addon,
    items_per_page: t.Annotated[int, Scope.SETTINGS],
    offset: t.Annotated[int, Scope.QUERY] = 0,
    folder_id: t.Annotated[t.Optional[int], Scope.QUERY] = None,
):
    if folder_id is None and offset < 1:
        tv_channels_url = addon.url_for('resources.lib.pages.rutube.list_tv_channels')
        tv_channels_item = xbmcgui.ListItem('[B][COLOR lightgreen]%s[/COLOR][/B]' % addon.localize('Channels'))
        tv_channels_item.setArt({'thumb': addon.get_path('resources/lib/assets/icons/live_tv.png')})
        yield tv_channels_url, tv_channels_item, True

        if addon.get_setting('boosty.enabled', bool):
            boosty_url = addon.url_for('resources.lib.pages.boosty.list_subscriptions')
            boosty_item = xbmcgui.ListItem('[B][COLOR orange]%s[/COLOR][/B]' % addon.localize('Boosty'))
            boosty_item.setArt({'thumb': addon.get_path('resources/lib/assets/services/boosty.jpg')})
            boosty_item.setInfo('video', {'plot': addon.localize('boosty.description')})
            yield boosty_url, boosty_item, True

    create_action = xbmcgui.ListItem('[B][COLOR cyan]%s[/COLOR][/B]' % addon.localize('Add item'))
    create_action.setArt({'thumb': addon.get_path('resources/lib/assets/icons/playlist_add.png')})
    create_action.setInfo('video', {'plot': addon.localize('Add a new directory, video link or service.')})
    create_action.setProperty('IsPlayable', 'false')
    yield addon.url_for(create_item, parent_id=folder_id), create_action, False

    items = Item.select(parent_id=folder_id, limit=items_per_page + 1, offset=offset)
    render_next_page = len(items) > items_per_page

    for i in items[:items_per_page]:
        url = url_construct(i.item_type, i)

        gui_item = xbmcgui.ListItem(label=i.title)
        gui_item.setInfo('video', {
            'plot': i.description,
            'duration': i.data.get('duration'),
            'aired': i.data.get('published', i.ts).strftime('%Y-%m-%d %H:%M:%S'),
        })
        gui_item.setArt({
            'thumb': i.thumbnail,
            'fanart': i.cover,
        })
        context_menu = [
            (
                addon.localize('Rename'),
                'RunPlugin(%s)' % addon.url_for(rename_item, item_id=i.id),
            ),
            (
                addon.localize('Delete'),
                'RunPlugin(%s)' % addon.url_for(delete_item, item_id=i.id),
            ),
        ]

        if not i.is_folder:
            gui_item.setProperty('IsPlayable', 'true')

        if i.item_type == ItemType.FOLDER:
            context_menu.insert(0, (
                addon.localize('Add item'),
                'RunPlugin(%s)' % addon.url_for(create_item, parent_id=i.id),
            ))

        gui_item.addContextMenuItems(context_menu)

        yield url, gui_item, i.is_folder

    if render_next_page:
        offset += items_per_page
        yield create_next_element(list_items, folder_id=folder_id, offset=offset)


@router.route
def create_item(
    parent_id: t.Annotated[t.Optional[int], Scope.QUERY] = None,
):
    title_or_url = prompt(current_addon.localize('Enter folder name or URL'), required=True)

    if title_or_url:
        try:
            media_provider.create_item(
                title_or_url=title_or_url.value,
                parent_id=parent_id,
            ).save()
            xbmc.executebuiltin('Container.Refresh()')
        except Exception as err:
            if current_addon.debug:
                raise
            alert(current_addon.localize('Error'), str(err))


@router.route
def delete_item(
    item_id: t.Annotated[str, Scope.QUERY],
):
    if xbmcgui.Dialog().yesno('Confirm action', 'Are you sure you want to delete the item?'):
        item = Item.find(item_id)

        if item is not None:
            item.delete()
            xbmc.executebuiltin('Container.Refresh()')


@router.route
def rename_item(
    item_id: t.Annotated[str, Scope.QUERY],
):
    item = Item.find(item_id)

    if item is None:
        alert('Error', f'Item with ID {item_id} not found.')
        return None

    title = prompt('Enter item title', required=True, default=item.title)

    if title:
        item.title = title.value
        item.save()
        xbmc.executebuiltin('Container.Refresh()')
