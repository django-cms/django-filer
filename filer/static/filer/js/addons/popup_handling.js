'use strict';

const windowname_to_id = (text) => {
    text = text.replace(/__dot__/g, '.');
    text = text.replace(/__dash__/g, '-');
    return text.split('__')[0];
};

window.dismissPopupAndReload = (win) => {
    document.location.reload();
    win.close();
};

window.dismissRelatedImageLookupPopup = (
    win,
    chosenId,
    chosenThumbnailUrl,
    chosenDescriptionTxt,
    chosenAdminChangeUrl
) => {
    const id = windowname_to_id(win.name);
    const lookup = document.getElementById(id);
    if (!lookup) {
        return;
    }
    const container = lookup.closest('.filerFile');
    if (!container) {
        return;
    }
    const edit = container.querySelector('.edit');
    const image = container.querySelector('.thumbnail_img');
    const descriptionText = container.querySelector('.description_text');
    const clearer = container.querySelector('.filerClearer');
    const dropzoneMessage = container.parentElement.querySelector('.dz-message');
    const element = container.querySelector('input');
    const oldId = element.value;

    element.value = chosenId;
    const dropzone = element.closest('.js-filer-dropzone');
    if (dropzone) {
        dropzone.classList.add('js-object-attached');
    }
    if (chosenThumbnailUrl && image) {
        image.src = chosenThumbnailUrl;
        image.classList.remove('hidden');
        image.removeAttribute('srcset');
    }
    if (descriptionText) {
        descriptionText.textContent = chosenDescriptionTxt;
    }
    if (clearer) {
        clearer.classList.remove('hidden');
    }
    lookup.classList.add('related-lookup-change');
    if (edit) {
        edit.classList.add('related-lookup-change');
    }
    if (chosenAdminChangeUrl && edit) {
        edit.setAttribute('href', `${chosenAdminChangeUrl}?_edit_from_widget=1`);
    }
    if (dropzoneMessage) {
        dropzoneMessage.classList.add('hidden');
    }

    if (oldId !== chosenId) {
        element.dispatchEvent(new Event('change', { bubbles: true }));
    }
    win.close();
};
window.dismissRelatedFolderLookupPopup = (win, chosenId, chosenName) => {
    const id = windowname_to_id(win.name);
    const lookup = document.getElementById(id);
    if (!lookup) {
        return;
    }
    const container = lookup.closest('.filerFile');
    if (!container) {
        return;
    }
    const image = container.querySelector('.thumbnail_img');
    const clearButton = document.getElementById(`id_${id}_clear`);
    const input = document.getElementById(`id_${id}`);
    const folderName = container.querySelector('.description_text');
    const addFolderButton = document.getElementById(id);

    if (input) {
        input.value = chosenId;
    }
    if (image) {
        image.classList.remove('hidden');
    }
    if (folderName) {
        folderName.textContent = chosenName;
    }
    if (clearButton) {
        clearButton.classList.remove('hidden');
    }
    if (addFolderButton) {
        addFolderButton.classList.add('hidden');
    }
    win.close();
};

// Handle popup dismiss links (for folder/image selection in popups)
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.js-dismiss-popup').forEach((link) => {
        link.addEventListener('click', function (e) {
            e.preventDefault();

            const fileId = this.dataset.fileId;
            const iconUrl = this.dataset.iconUrl;
            const label = this.dataset.label;

            if (this.classList.contains('js-dismiss-image')) {
                const changeUrl = this.dataset.changeUrl || '';
                window.opener.dismissRelatedImageLookupPopup(
                    window,
                    fileId,
                    iconUrl,
                    label,
                    changeUrl
                );
            } else if (this.classList.contains('js-dismiss-folder')) {
                window.opener.dismissRelatedFolderLookupPopup(window, fileId, label);
            }
        });
    });

    // Auto-dismiss popup on page load (for dismiss_popup.html)
    const popupData = document.getElementById('popup-dismiss-data');
    if (popupData && window.opener) {
        const pk = popupData.dataset.pk;
        const label = popupData.dataset.label;
        window.opener.dismissRelatedPopup(window, pk, label);
    }
});
