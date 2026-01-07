// #DROPZONE#
// This script implements the dropzone settings
'use strict';

import Dropzone from 'dropzone';

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
    const progressSelector = '.js-filer-dropzone-progress';
    const previewImageWrapperSelector = '.js-img-wrapper';
    const filerClearerSelector = '.filerClearer';
    const fileChooseSelector = '.js-file-selector';
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

        new Dropzone(dropzone, {
            url: dropzoneUrl,
            paramName: 'file',
            maxFiles: 1,
            maxFilesize: dropzone.dataset.maxFilesize,
            // previewTemplate: document.querySelector(dropzoneTemplateSelector)?.innerHTML || '',
            clickable: false,
            addRemoveLinks: false,
            init: function () {
                checkMinWidth(dropzone);

                this.on('removedfile', () => {
                    if (fileChoose) {
                        fileChoose.style.display = '';
                    }
                    dropzone.classList.remove(objectAttachedClass);
                    this.removeAllFiles();
                    clearButton?.click();
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
            maxfilesexceeded: function () {
                this.removeAllFiles(true);
            },
            drop: function () {
                this.removeAllFiles(true);
                const progressEl = dropzone.querySelector(progressSelector);
                if (progressEl) {
                    progressEl.classList.remove(hiddenClass);
                }
                if (fileChoose) {
                    fileChoose.style.display = 'block';
                }
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
                } else {
                    if (response && response.error) {
                        showError(`${file.name}: ${response.error}`);
                    }
                    this.removeAllFiles(true);
                }

                const images = this.element.querySelectorAll('img');
                images.forEach((img) => {
                    img.addEventListener('dragstart', (event) => {
                        event.preventDefault();
                    });
                });
            },
            error: function (file, msg, response) {
                if (response && response.error) {
                    msg += ` ; ${response.error}`;
                }
                showError(`${file.name}: ${msg}`);
                this.removeAllFiles(true);
            },
            reset: function () {
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
                dropzone.classList.remove(objectAttachedClass);
                if (inputId) {
                    inputId.value = '';
                }
                lookupButton?.classList.remove('related-lookup-change');
                editButton?.classList.remove('related-lookup-change');
                message?.classList.remove(hiddenClass);
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
