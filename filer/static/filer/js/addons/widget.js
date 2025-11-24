'use strict';

document.addEventListener('DOMContentLoaded', () => {
    const filer_clear = (ev) => {
        ev.preventDefault();

        const clearer = ev.currentTarget;
        const container = clearer.closest('.filerFile');
        if (!container) {
            return;
        }

        const input = container.querySelector('input');
        const thumbnail = container.querySelector('.thumbnail_img');
        const description = container.querySelector('.description_text');
        const addImageButton = container.querySelector('.lookup');
        const editImageButton = container.querySelector('.edit');
        const dropzoneMessage = container.parentElement.querySelector('.dz-message');
        const hiddenClass = 'hidden';

        clearer.classList.add(hiddenClass);
        if (input) {
            input.value = '';
        }
        if (thumbnail) {
            thumbnail.classList.add(hiddenClass);
            var thumbnailLink = thumbnail.parentElement;
            if (thumbnailLink.tagName === 'A') {
                thumbnailLink.removeAttribute('href');
            }
        }
        if (addImageButton) {
            addImageButton.classList.remove('related-lookup-change');
        }
        if (editImageButton) {
            editImageButton.classList.remove('related-lookup-change');
        }
        if (dropzoneMessage) {
            dropzoneMessage.classList.remove(hiddenClass);
        }
        if (description) {
            description.textContent = '';
        }
    };

    const foreignKeyFields = document.querySelectorAll('.filerFile .vForeignKeyRawIdAdminField');
    foreignKeyFields.forEach((field) => {
        field.setAttribute('type', 'hidden');
    });

    // Remove any existing handlers and add new ones
    const clearers = document.querySelectorAll('.filerFile .filerClearer');
    clearers.forEach((clearer) => {
        clearer.addEventListener('click', filer_clear);
    });
});
