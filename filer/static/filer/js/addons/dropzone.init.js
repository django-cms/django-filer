// #DROPZONE#
// This script implements the dropzone settings
'use strict';

import Dropzone from 'dropzone';

import { getCsrfToken } from './csrf.js';

if (Dropzone) {
    Dropzone.autoDiscover = false;
}

document.addEventListener('DOMContentLoaded', () => {
    const previewImageSelector = '.js-img-preview';
    const dropzoneSelector = '.js-filer-dropzone';
    const dropzones = document.querySelectorAll(dropzoneSelector);
    const messageSelector = '.js-filer-dropzone-message';
    const lookupButtonSelector = '.js-related-lookup';
    const editButtonSelector = '.js-related-edit';
    const dropzoneTemplate = '.js-filer-dropzone-template';
    const progressSelector = '.js-filer-dropzone-progress';
    const previewImageWrapperSelector = '.js-img-wrapper';
    const filerClearerSelector = '.filerClearer';
    const fileChooseSelector = '.js-file-selector';
    const thumbnailSelector = '.thumbnail_img';
    const descriptionSelector = '.description_text';
    const fileIdInputSelector = '.vForeignKeyRawIdAdminField';
    const dragHoverClass = 'dz-drag-hover';
    const hiddenClass = 'hidden';
    const mobileClass = 'filer-dropzone-mobile';
    const objectAttachedClass = 'js-object-attached';
    const minWidth = 500;

    const checkMinWidth = (element) => {
        const width = element.offsetWidth;
        if (width < minWidth) {
            element.classList.add(mobileClass);
        } else {
            element.classList.remove(mobileClass);
        }
    };

    const showError = (message) => {
        try {
            window.parent.CMS.API.Messages.open({
                message: message
            });
        } catch {
            if (window.filerShowError) {
                window.filerShowError(message);
            } else {
                alert(message);
            }
        }
    };

    const createDropzone = function (dropzone) {
        const dropzoneUrl = dropzone.dataset.url;
        const inputId = dropzone.querySelector(fileIdInputSelector);
        const isImage = inputId?.getAttribute('name') === 'image';
        const lookupButton = dropzone.querySelector(lookupButtonSelector);
        const editButton = dropzone.querySelector(editButtonSelector);
        const message = dropzone.querySelector(messageSelector);
        const clearButton = dropzone.querySelector(filerClearerSelector);
        const fileChoose = dropzone.querySelector(fileChooseSelector);

        if (dropzone.dropzone) {
            return;
        }

        const resizeHandler = () => {
            checkMinWidth(dropzone);
        };
        window.addEventListener('resize', resizeHandler);

        // The dropzone preview and the widget's own file representation are both
        // positioned absolutely inside the dropzone. Only ever show one of them:
        // the preview while a dropped file is being uploaded, the widget's own
        // markup before and after. Otherwise they overlap and the widget's
        // buttons end up covered by the preview (#1573).
        const showFileRepresentation = (visible) => {
            if (fileChoose) {
                fileChoose.style.display = visible ? '' : 'none';
            }
        };

        // Bring the widget's file representation in line with the file that was
        // just uploaded, so that it shows the same as it would after a reload.
        const updateFileRepresentation = (response) => {
            if (!fileChoose) {
                return;
            }
            const thumbnail = fileChoose.querySelector(thumbnailSelector);
            const description = fileChoose.querySelector(descriptionSelector);

            if (thumbnail) {
                // The srcset still points at the previously selected file
                thumbnail.removeAttribute('srcset');
                thumbnail.src = response.thumbnail_180 || clearButton?.dataset.noIconFile || thumbnail.src;
                thumbnail.alt = response.alt_text || '';
                thumbnail.classList.remove(hiddenClass);
                const link = thumbnail.parentElement;
                if (link?.tagName === 'A') {
                    if (response.original_image) {
                        link.href = response.original_image;
                    } else {
                        link.removeAttribute('href');
                    }
                }
            }
            if (description) {
                description.textContent = response.label || '';
            }
            if (editButton && response.change_url) {
                editButton.href = `${response.change_url}?_edit_from_widget=1`;
            }
            clearButton?.classList.remove(hiddenClass);
        };

        // The widget's appearance when it holds no file
        const showEmptyState = () => {
            dropzone.classList.remove(objectAttachedClass);
            lookupButton?.classList.remove('related-lookup-change');
            editButton?.classList.remove('related-lookup-change');
            message?.classList.remove(hiddenClass);
        };

        // Dropzone emits "removedfile" both when the user removes a file and when
        // the code below discards previews it no longer needs. Only the former
        // should clear the widget.
        // Nesting level of the element the pointer is over while dragging, see
        // the dragenter/dragleave handlers below
        let dragDepth = 0;
        let removingPreviews = false;
        const discardPreviews = (dz) => {
            removingPreviews = true;
            dz.removeAllFiles(true);
            removingPreviews = false;
        };

        new Dropzone(dropzone, {
            url: dropzoneUrl,
            headers: { 'X-CSRFToken': getCsrfToken() },
            paramName: 'file',
            maxFiles: 1,
            maxFilesize: dropzone.dataset.maxFilesize,
            previewTemplate: document.querySelector(dropzoneTemplate).innerHTML || '',
            clickable: false,
            addRemoveLinks: false,
            init: function () {
                checkMinWidth(dropzone);

                this.on('removedfile', () => {
                    showFileRepresentation(true);
                    if (removingPreviews) {
                        return;
                    }
                    dropzone.classList.remove(objectAttachedClass);
                    discardPreviews(this);
                    clearButton?.click();
                    if (inputId) {
                        const changeEvent = new Event('change', { bubbles: true });
                        inputId.dispatchEvent(changeEvent);
                    }
                });

                const images = this.element.querySelectorAll('img');
                images.forEach((img) => {
                    img.addEventListener('dragstart', (event) => {
                        event.preventDefault();
                    });
                });

                if (clearButton) {
                    clearButton.addEventListener('click', () => {
                        dropzone.classList.remove(objectAttachedClass);
                        // const changeEvent = new Event('change', { bubbles: true });
                        // inputId?.dispatchEvent(changeEvent);
                    });
                }
            },
            dragenter: function () {
                dragDepth += 1;
                dropzone.classList.add(dragHoverClass);
            },
            dragleave: function () {
                // dragleave also fires when the pointer moves from one of the
                // dropzone's children to the next. Counting the enters keeps the
                // drag state stable until the pointer really left (#1573).
                dragDepth = Math.max(dragDepth - 1, 0);
                if (dragDepth === 0) {
                    dropzone.classList.remove(dragHoverClass);
                }
            },
            dragend: function () {
                dragDepth = 0;
                dropzone.classList.remove(dragHoverClass);
            },
            maxfilesexceeded: function () {
                discardPreviews(this);
                showFileRepresentation(true);
            },
            drop: function () {
                dragDepth = 0;
                discardPreviews(this);
                const progressEl = dropzone.querySelector(progressSelector);
                if (progressEl) {
                    progressEl.classList.remove(hiddenClass);
                }
                // Hand the widget over to the dropzone preview for the duration of
                // the upload. The current selection is kept until the upload
                // succeeded, so that a failed upload leaves the widget untouched.
                showFileRepresentation(false);
                lookupButton?.classList.add('related-lookup-change');
                editButton?.classList.add('related-lookup-change');
                message?.classList.add(hiddenClass);
                dropzone.classList.remove(dragHoverClass);
                dropzone.classList.add(objectAttachedClass);
            },
            success: function (file, response) {
                const progressEl = dropzone.querySelector(progressSelector);
                if (progressEl) {
                    progressEl.classList.add(hiddenClass);
                }

                if (file && file.status === 'success' && response) {
                    if (response.file_id && inputId) {
                        inputId.value = response.file_id;
                        const changeEvent = new Event('change', { bubbles: true });
                        inputId.dispatchEvent(changeEvent);
                    }
                    if (response.thumbnail_180 && isImage) {
                        const previewImg = dropzone.querySelector(previewImageSelector);
                        if (previewImg) {
                            previewImg.style.backgroundImage = `url(${response.thumbnail_180})`;
                        }
                        const wrapper = dropzone.querySelector(previewImageWrapperSelector);
                        if (wrapper) {
                            wrapper.classList.remove(hiddenClass);
                        }
                    }
                    // The upload is done: the widget shows the new file itself,
                    // the dropzone preview is no longer needed.
                    updateFileRepresentation(response);
                    discardPreviews(this);
                } else {
                    if (response && response.error) {
                        showError(`${file.name}: ${response.error}`);
                    }
                    discardPreviews(this);
                }
                showFileRepresentation(true);

                const images = this.element.querySelectorAll('img');
                images.forEach((img) => {
                    img.addEventListener('dragstart', (event) => {
                        event.preventDefault();
                    });
                });
            },
            error: function (file, msg) {
                // Dropzone hands over the parsed JSON body when the server rejects
                // an upload; filer reports the reason in "error".
                const message = (msg && (msg.error || msg.message)) || msg;

                showError(`${file.name}: ${message}`);
                // Restore the widget: the failed upload did not change the selection
                discardPreviews(this);
                showFileRepresentation(true);
                if (!inputId?.value) {
                    showEmptyState();
                }
            },
            reset: function () {
                // Dropzone resets when its last preview is removed - which also
                // happens when a finished upload's preview is discarded. Only an
                // actual removal by the user empties the widget.
                if (removingPreviews) {
                    return;
                }
                if (isImage) {
                    const wrapper = dropzone.querySelector(previewImageWrapperSelector);
                    if (wrapper) {
                        wrapper.classList.add(hiddenClass);
                    }
                    const previewImg = dropzone.querySelector(previewImageSelector);
                    if (previewImg) {
                        previewImg.style.backgroundImage = 'none';
                    }
                }
                if (inputId) {
                    inputId.value = '';
                }
                showEmptyState();
                if (inputId) {
                    const changeEvent = new Event('change', { bubbles: true });
                    inputId.dispatchEvent(changeEvent);
                }
            }
        });
    };

    if (dropzones.length && Dropzone) {
        if (!window.filerDropzoneInitialized) {
            window.filerDropzoneInitialized = true;
            Dropzone.autoDiscover = false;
        }
        dropzones.forEach(createDropzone);

        // Handle initialization of the dropzone on dynamic formsets (i.e. Django admin inlines)
        document.addEventListener('formset:added', (event) => {
            let dropzones;
            let rowIdx;
            let row;

            if (event.detail && event.detail.formsetName) {
                /*
                    Django 4.1 changed the event type being fired when adding
                    a new formset from a jQuery to a vanilla JavaScript event.
                    https://docs.djangoproject.com/en/4.1/ref/contrib/admin/javascript/

                    In this case we find the newly added row and initialize the
                    dropzone on any dropzoneSelector on that row.
                */

                rowIdx = parseInt(
                    document.getElementById(
                        `id_${event.detail.formsetName}-TOTAL_FORMS`
                    ).value, 10
                ) - 1;
                row = document.getElementById(`${event.detail.formsetName}-${rowIdx}`);
                dropzones = row?.querySelectorAll(dropzoneSelector) || [];
            } else {
                // Fallback for older jQuery event format
                row = event.target;
                dropzones = row?.querySelectorAll(dropzoneSelector) || [];
            }

            dropzones?.forEach(createDropzone);
        });
    }
});
