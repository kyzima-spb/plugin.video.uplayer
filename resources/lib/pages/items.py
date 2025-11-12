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
import xbmc
import xbmcgui

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
    return current_addon.url_for(play_video, url=item.url)


@router.route
def play_video(addon: Addon, url: t.Annotated[str, Scope.QUERY]):
    import webbrowser
    webbrowser.open(url)


@router.route(is_root=True)
@Directory(
    ltitle='',
    content=Content.VIDEOS,
    cache_to_disk=False,
)
def list_items(
    addon: Addon,
    items_per_page: t.Annotated[int, Scope.SETTINGS],
    offset: t.Annotated[int, Scope.QUERY] = 0,
    folder_id: t.Annotated[t.Optional[int], Scope.QUERY] = None,
):
    if folder_id is None and offset < 1 and addon.get_setting('boosty.enabled', bool):
        boosty_url = addon.url_for('resources.lib.pages.boosty.list_subscriptions')
        boosty_item = xbmcgui.ListItem('[B][COLOR orange]Boosty[/COLOR][/B]')
        boosty_item.setArt({'thumb': addon.get_path('resources/lib/assets/services/boosty.jpg')})
        boosty_item.setInfo('video', {'plot': addon.localize('boosty.description')})
        yield boosty_url, boosty_item, True

    create_action = xbmcgui.ListItem(label='[B][COLOR cyan]Add item[/COLOR][/B]')
    create_action.setArt({'thumb': addon.get_path('resources/lib/assets/icons/add.png')})
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
        })
        gui_item.setArt({
            'thumb': i.thumbnail,
            'fanart': i.cover,
        })
        context_menu = [
            (
                'Rename',
                'RunPlugin(%s)' % addon.url_for(rename_item, item_id=i.id),
            ),
            (
                'Delete',
                'RunPlugin(%s)' % addon.url_for(delete_item, item_id=i.id),
            ),
        ]

        if not i.is_folder:
            gui_item.setProperty('IsPlayable', 'true')

        if i.item_type == ItemType.FOLDER:
            context_menu.insert(0, (
                'Add item', 'RunPlugin(%s)' % addon.url_for(create_item, parent_id=i.id),
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
    title_or_url = prompt('Enter item title or URL', required=True)

    if title_or_url:
        media_provider.create_item(
            title_or_url=title_or_url.value,
            parent_id=parent_id,
        ).save()
        xbmc.executebuiltin('Container.Refresh()')


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
