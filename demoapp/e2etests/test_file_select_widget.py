"""
End-to-end tests for the ``<finder-file-select>`` and ``<finder-folder-select>``
web components, which the model fields of ``demoapp.models.DemoAppModel`` render.

Both components live in a shadow root; Playwright pierces those with plain CSS
selectors.
"""

import pytest

from django.urls import reverse

from demoapp.models import DemoAppModel

pytestmark = pytest.mark.django_db(transaction=True)

FILE_SELECT = 'finder-file-select'
FOLDER_SELECT = 'finder-folder-select'


def open_dialog(page):
    """Click the widget preview and wait for the file browser to have loaded."""
    page.locator(f'{FILE_SELECT} .finder-file-select figure').click()
    page.wait_for_selector(f'{FILE_SELECT} ul.files-browser')
    return page.locator(f'{FILE_SELECT} dialog')


def test_widget_renders_placeholder(demoapp_page):
    page = demoapp_page
    page.wait_for_selector(f'{FILE_SELECT} .finder-file-select')
    assert page.locator(f'{FILE_SELECT} .finder-file-select figure').inner_text() == "Select File"
    # the widget keeps the value in a hidden input rendered by Django
    assert page.locator('input#id_file').input_value() == ''
    assert page.locator(f'{FILE_SELECT} dialog').get_attribute('open') is None


def test_dialog_lists_the_files_of_the_root_folder(demoapp_page, image_file):
    page = demoapp_page
    page.reload()
    open_dialog(page)

    files = page.locator(f'{FILE_SELECT} ul.files-browser > li')
    assert files.count() == 1
    assert files.first.locator('figcaption').inner_text() == 'image_0.png'


def test_dialog_reports_an_empty_folder(demoapp_page):
    page = demoapp_page
    open_dialog(page)
    assert page.locator(f'{FILE_SELECT} ul.files-browser li.status').inner_text() == "Empty folder"


def test_select_file_updates_the_input(demoapp_page, image_file):
    page = demoapp_page
    page.reload()
    dialog = open_dialog(page)

    page.locator(f'{FILE_SELECT} ul.files-browser > li').first.click()
    page.wait_for_selector(f'{FILE_SELECT} .finder-file-select figcaption')

    assert dialog.get_attribute('open') is None, "selecting a file closes the dialog"
    assert page.locator('input#id_file').input_value() == str(image_file.id)
    preview = page.locator(f'{FILE_SELECT} .finder-file-select figcaption')
    assert 'image_0.png' in preview.inner_text()
    assert 'image/png' in preview.inner_text()


def test_submitting_the_form_stores_the_selected_file(demoapp_page, image_file):
    page = demoapp_page
    page.reload()
    open_dialog(page)
    page.locator(f'{FILE_SELECT} ul.files-browser > li').first.click()
    page.wait_for_selector(f'{FILE_SELECT} .finder-file-select figcaption')

    page.locator('form button[type="submit"]').click()
    page.wait_for_load_state()

    assert DemoAppModel.objects.get().file == image_file
    # after reloading, the widget shows the stored file again
    assert 'image_0.png' in page.locator(f'{FILE_SELECT} .finder-file-select figcaption').inner_text()


def test_remove_the_selected_file(demoapp_page, image_file):
    page = demoapp_page
    page.reload()
    open_dialog(page)
    page.locator(f'{FILE_SELECT} ul.files-browser > li').first.click()
    page.wait_for_selector(f'{FILE_SELECT} .remove-file-button')

    page.locator(f'{FILE_SELECT} .remove-file-button').click()
    page.wait_for_selector(f'{FILE_SELECT} .finder-file-select figure strong')

    assert page.locator('input#id_file').input_value() == ''
    assert page.locator(f'{FILE_SELECT} .finder-file-select figure').inner_text() == "Select File"


def test_dialog_can_be_dismissed(demoapp_page, image_file):
    page = demoapp_page
    page.reload()
    dialog = open_dialog(page)
    assert dialog.get_attribute('open') is not None

    page.locator(f'{FILE_SELECT} .close-button[role="button"]').click()
    page.wait_for_function(
        f'() => !document.querySelector("{FILE_SELECT}").shadowRoot.querySelector("dialog").open'
    )
    assert page.locator('input#id_file').input_value() == ''


# FIXME: both web components install their own ``keydown`` listener on ``window``,
# so Escape also dismisses the never-opened dialog of ``<finder-folder-select>``.
# That one has no folder loaded yet and requests ``/finder-api/null/list``, which
# the server answers with 404 and the client logs as an error.
@pytest.mark.allow_js_errors
def test_escape_closes_the_dialog(demoapp_page, image_file):
    page = demoapp_page
    page.reload()
    dialog = open_dialog(page)
    assert dialog.get_attribute('open') is not None

    page.keyboard.press('Escape')
    page.wait_for_function(
        f'() => !document.querySelector("{FILE_SELECT}").shadowRoot.querySelector("dialog").open'
    )


def test_uploading_a_file_from_the_dialog(demoapp_page, root_folder, assets_dir):
    """Uploading opens the editor for the new file; saving it selects the file."""
    page = demoapp_page
    dialog = open_dialog(page)

    page.locator(f'{FILE_SELECT} input[type="file"][name="file:{root_folder.id}"]').set_input_files(
        assets_dir / 'image_1.png'
    )
    page.wait_for_selector(f'{FILE_SELECT} .browser-editor')
    assert root_folder.listdir(is_folder=False).count() == 1

    page.locator(f'{FILE_SELECT} .button-row button.default').click()
    page.wait_for_selector(f'{FILE_SELECT} .finder-file-select figcaption')

    assert dialog.get_attribute('open') is None
    uploaded = root_folder.listdir(is_folder=False).get()
    assert page.locator('input#id_file').input_value() == str(uploaded['id'])


def test_dismissing_an_upload_removes_the_file(demoapp_page, root_folder, assets_dir):
    page = demoapp_page
    open_dialog(page)

    page.locator(f'{FILE_SELECT} input[type="file"][name="file:{root_folder.id}"]').set_input_files(
        assets_dir / 'image_1.png'
    )
    page.wait_for_selector(f'{FILE_SELECT} .browser-editor')
    page.locator(f'{FILE_SELECT} .button-row button.dismiss').click()
    page.wait_for_function(
        f'() => !document.querySelector("{FILE_SELECT}").shadowRoot.querySelector("dialog").open'
    )

    assert page.locator('input#id_file').input_value() == ''
    assert root_folder.listdir(is_folder=False).count() == 0


def test_folder_widget_renders_placeholder(demoapp_page):
    page = demoapp_page
    page.wait_for_selector(f'{FOLDER_SELECT} .finder-file-select')
    assert page.locator(f'{FOLDER_SELECT} .finder-file-select figure').inner_text() == "Select Folder"
    assert page.locator('input#id_folder').input_value() == ''


@pytest.fixture
def cms_modal_page(page, connector, ambit):
    """The demo form in an iframe inside a django CMS like modal."""
    page.goto(connector.url(reverse('cms-modal')))
    frame = page.frame_locator('.cms-modal iframe')
    frame.locator(f'{FILE_SELECT} .finder-file-select').wait_for()
    return page, frame


def open_parent_dialog(page, frame):
    frame.locator(f'{FILE_SELECT} .finder-file-select figure').click()
    page.wait_for_selector('.finder-dialog-host dialog[open] ul.files-browser')
    return page.locator('.finder-dialog-host dialog[open]')


def test_dialog_opens_in_parent_of_cms_modal(image_file, cms_modal_page):
    page, frame = cms_modal_page
    dialog = open_parent_dialog(page, frame)

    # the dialog uses the whole window rather than the iframe of the modal
    assert frame.locator(f'{FILE_SELECT} dialog').count() == 0
    assert dialog.bounding_box()['width'] > 600

    dialog.locator('ul.files-browser > li').first.click()
    frame.locator(f'{FILE_SELECT} .finder-file-select figcaption').wait_for()
    assert frame.locator('input#id_file').input_value() == str(image_file.id)
    assert page.locator('.finder-dialog-host dialog[open]').count() == 0


def test_escape_closes_the_dialog_but_not_the_cms_modal(cms_modal_page):
    page, frame = cms_modal_page
    open_parent_dialog(page, frame)

    page.keyboard.press('Escape')
    page.wait_for_selector('.finder-dialog-host dialog[open]', state='detached')
    assert page.evaluate('window.cmsModalClosed') is False


def test_dialog_host_is_removed_with_the_cms_modal(cms_modal_page):
    page, frame = cms_modal_page
    assert page.locator('.finder-dialog-host').count() == 2  # file and folder select
    page.evaluate("document.querySelector('.cms-modal iframe').src = 'about:blank'")
    page.wait_for_selector('.finder-dialog-host', state='detached')


def test_dialog_stays_in_an_iframe_outside_of_a_cms_modal(image_file, page, connector, ambit):
    page.goto(connector.url(reverse('cms-modal') + '?modal=0'))
    frame = page.frame_locator('.other-container iframe')
    frame.locator(f'{FILE_SELECT} .finder-file-select figure').click()
    frame.locator(f'{FILE_SELECT} dialog[open] ul.files-browser').wait_for()
    assert page.locator('.finder-dialog-host').count() == 0
