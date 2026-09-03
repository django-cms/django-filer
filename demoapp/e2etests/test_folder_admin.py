"""
End-to-end tests for the React based folder admin, ``client/admin/FolderAdmin.tsx``.
"""

import pytest

from finder.models.file import FileModel
from finder.models.folder import FolderModel

pytestmark = pytest.mark.django_db(transaction=True)

#: Layout buttons of the menu bar, in the order they are rendered.
LAYOUTS = ['tiles', 'mosaic', 'list', 'columns', 'gallery']

#: Action buttons of the menu bar, in the order they are rendered.
ACTIONS = ['cut', 'paste', 'trash']


def layout_button(page, layout):
    return page.locator('#content-react nav li[role="menuitem"][aria-selected]').nth(LAYOUTS.index(layout))


def action_button(page, action):
    return page.locator('#content-react nav li[role="menuitem"][aria-disabled]').nth(ACTIONS.index(action))


def extra_menu_item(page, label):
    """Open the “Extra options” drop down menu and return the entry with the given label."""
    extra_menu = page.locator('#content-react nav li.extra-menu')
    if extra_menu.get_attribute('aria-expanded') == 'false':
        extra_menu.locator('div').first.click()
    return extra_menu.locator('ul[role="listbox"] > li', has_text=label).first


def inodes(page):
    return page.locator('#content-react ul.inode-list li[data-id]')


def upload(page, folder, *file_names, assets_dir):
    page.locator(f'input[type="file"][name="file:{folder.id}"]').set_input_files(
        [assets_dir / file_name for file_name in file_names]
    )
    inodes(page).nth(len(file_names) - 1).wait_for()


def test_empty_folder_shows_placeholder(folder_admin_page):
    placeholder = folder_admin_page.locator('#content-react ul.inode-list li.status')
    assert placeholder.inner_text() == "This folder is empty"


def test_menu_bar_renders_all_layouts(folder_admin_page):
    buttons = folder_admin_page.locator('#content-react nav li[role="menuitem"][aria-selected]')
    assert buttons.count() == len(LAYOUTS)
    # tiles is the default layout
    assert buttons.nth(0).get_attribute('aria-selected') == 'true'
    assert folder_admin_page.locator('#content-react div.work-area.tiles').count() == 1


@pytest.mark.parametrize('layout', ['mosaic', 'list', 'columns', 'gallery'])
def test_switch_layout(folder_admin_page, layout):
    page = folder_admin_page
    layout_button(page, layout).click()
    page.wait_for_selector(f'#content-react div.work-area.{layout}')
    assert layout_button(page, layout).get_attribute('aria-selected') == 'true'
    # the chosen layout is remembered in a cookie
    cookies = {cookie['name']: cookie['value'] for cookie in page.context.cookies()}
    assert cookies['django-finder-layout'] == layout


def test_add_new_folder(folder_admin_page, root_folder):
    page = folder_admin_page
    page.once('dialog', lambda dialog: dialog.accept('Pictures'))
    extra_menu_item(page, "Add new folder").click()

    inodes(page).first.wait_for()
    assert inodes(page).first.locator('.inode-name').inner_text() == 'Pictures'
    assert FolderModel.objects.filter(parent=root_folder, name='Pictures').exists()


def test_add_new_folder_can_be_cancelled(folder_admin_page, root_folder):
    page = folder_admin_page
    page.once('dialog', lambda dialog: dialog.dismiss())
    extra_menu_item(page, "Add new folder").click()

    page.wait_for_timeout(300)
    assert inodes(page).count() == 0
    assert not FolderModel.objects.filter(parent=root_folder).exists()


def test_add_folder_rejects_duplicate_name(folder_admin_page, root_folder, admin_user):
    FolderModel.objects.create(parent=root_folder, name='Pictures', owner=admin_user)
    page = folder_admin_page
    page.reload()
    inodes(page).first.wait_for()

    messages = []

    def handle_dialog(dialog):
        messages.append(dialog.message)
        dialog.accept('Pictures') if dialog.type == 'prompt' else dialog.dismiss()

    page.on('dialog', handle_dialog)
    extra_menu_item(page, "Add new folder").click()
    page.wait_for_timeout(500)

    assert messages[-1] == "A folder named “Pictures” already exists."
    assert FolderModel.objects.filter(parent=root_folder, name='Pictures').count() == 1


def test_upload_image(folder_admin_page, root_folder, assets_dir):
    page = folder_admin_page
    upload(page, root_folder, 'image_0.png', assets_dir=assets_dir)

    assert inodes(page).first.locator('.inode-name').inner_text() == 'image_0.png'
    file_obj = FileModel.objects.get_inode(parent=root_folder, name='image_0.png')
    assert file_obj.mime_type == 'image/png'


def test_upload_multiple_images(folder_admin_page, root_folder, assets_dir):
    page = folder_admin_page
    upload(page, root_folder, 'image_0.png', 'image_1.png', 'image_2.png', assets_dir=assets_dir)

    assert inodes(page).count() == 3
    # uploaded PNGs are stored as ``PILImageModel``, so list them through the folder
    assert root_folder.listdir(is_folder=False).count() == 3


def test_open_subfolder(folder_admin_page, root_folder, admin_user):
    sub_folder = FolderModel.objects.create(parent=root_folder, name='Sub Folder', owner=admin_user)
    page = folder_admin_page
    page.reload()
    folder = page.locator(f'#content-react ul.inode-list li[data-id="{sub_folder.id}"]')
    folder.wait_for()
    folder.dblclick()

    page.wait_for_url(f'**/{sub_folder.id}')
    page.wait_for_selector('#content-react ul.inode-list')
    assert page.locator('#content-react ul.inode-list li.status').inner_text() == "This folder is empty"


def test_click_selects_an_inode(folder_admin_page, root_folder, assets_dir):
    page = folder_admin_page
    upload(page, root_folder, 'image_0.png', 'image_1.png', assets_dir=assets_dir)

    # the actions operating on a selection are disabled while nothing is selected
    assert action_button(page, 'trash').get_attribute('aria-disabled') == 'true'

    inodes(page).first.click()
    page.wait_for_selector('#content-react ul.inode-list li[data-id].selected')
    assert 'selected' in inodes(page).nth(0).get_attribute('class').split()
    assert 'selected' not in inodes(page).nth(1).get_attribute('class').split()
    assert action_button(page, 'trash').get_attribute('aria-disabled') == 'false'


def test_move_file_to_trash(folder_admin_page, root_folder, assets_dir):
    page = folder_admin_page
    upload(page, root_folder, 'image_0.png', assets_dir=assets_dir)
    file_obj = FileModel.objects.get_inode(parent=root_folder, name='image_0.png')

    inodes(page).first.click()
    page.wait_for_selector('#content-react ul.inode-list li[data-id].selected')
    action_button(page, 'trash').click()

    page.wait_for_selector('#content-react ul.inode-list li.status')
    assert inodes(page).count() == 0
    assert root_folder.listdir().count() == 0
    # the file has been moved into the trash folder rather than being erased
    file_obj.refresh_from_db()
    assert file_obj.parent_id != root_folder.id
