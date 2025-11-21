// #UPLOAD BUTTON#
// This script implements the upload button logic
'use strict';

import Dropzone from 'dropzone';

/* globals Cl */

document.addEventListener('DOMContentLoaded', () => {
    let submitNum = 0;
    let maxSubmitNum = 1;
    const uploadButton = document.querySelector('.js-upload-button');
    if (!uploadButton) {
        return;
    }

    const uploadButtonDisabled = document.querySelector('.js-upload-button-disabled');
    const uploadUrl = uploadButton.dataset.url;
    const uploadWelcome = document.querySelector('.js-filer-dropzone-upload-welcome');
    const uploadInfoContainer = document.querySelector('.js-filer-dropzone-upload-info-container');
    const uploadInfo = document.querySelector('.js-filer-dropzone-upload-info');
    const uploadNumber = document.querySelector('.js-filer-dropzone-upload-number');
    const uploadFileNameSelector = '.js-filer-dropzone-file-name';
    const uploadProgressSelector = '.js-filer-dropzone-progress';
    const uploadSuccess = document.querySelector('.js-filer-dropzone-upload-success');
    const uploadCanceled = document.querySelector('.js-filer-dropzone-upload-canceled');
    const uploadCancel = document.querySelector('.js-filer-dropzone-cancel');
    const infoMessage = document.querySelector('.js-filer-dropzone-info-message');
    const hiddenClass = 'hidden';
    const maxUploaderConnections = parseInt(uploadButton.dataset.maxUploaderConnections || 3, 10);
    const maxFilesize = parseInt(uploadButton.dataset.maxFilesize || 0, 10);
    let hasErrors = false;

    const updateUploadNumber = () => {
        if (uploadNumber) {
            uploadNumber.textContent = `${maxSubmitNum - submitNum}/${maxSubmitNum}`;
        }
    };

    const removeButton = () => {
        if (uploadButton) {
            uploadButton.remove();
        }
    };

    // utility
    const updateQuery = (uri, key, value) => {
        const re = new RegExp(`([?&])${key}=.*?(&|$)`, 'i');
        const separator = uri.indexOf('?') !== -1 ? '&' : '?';
        const hash = window.location.hash;
        uri = uri.replace(/#.*$/, '');
        if (uri.match(re)) {
            return uri.replace(re, `$1${key}=${value}$2`) + hash;
        } else {
            return uri + separator + key + '=' + value + hash;
        }
    };

    const reloadOrdered = () => {
        const uri = window.location.toString();
        window.location.replace(updateQuery(uri, 'order_by', '-modified_at'));
    };

    Cl.mediator.subscribe('filer-upload-in-progress', removeButton);

    // Initialize Dropzone on the upload button
    Dropzone.autoDiscover = false;
    const dropzone = new Dropzone(uploadButton, {
        url: uploadUrl,
        paramName: 'file',
        maxFilesize: maxFilesize,  // already in MB
        parallelUploads: maxUploaderConnections,
        clickable: uploadButton,
        previewTemplate: '<div></div>',
        addRemoveLinks: false,
        autoProcessQueue: true
    });

    dropzone.on('addedfile', () => {
        Cl.mediator.remove('filer-upload-in-progress', removeButton);
        Cl.mediator.publish('filer-upload-in-progress');
        submitNum++;

        maxSubmitNum = dropzone.files.length;

        if (infoMessage) {
            infoMessage.classList.remove(hiddenClass);
        }
        if (uploadWelcome) {
            uploadWelcome.classList.add(hiddenClass);
        }
        if (uploadSuccess) {
            uploadSuccess.classList.add(hiddenClass);
        }
        if (uploadInfoContainer) {
            uploadInfoContainer.classList.remove(hiddenClass);
        }
        if (uploadCancel) {
            uploadCancel.classList.remove(hiddenClass);
        }
        if (uploadCanceled) {
            uploadCanceled.classList.add(hiddenClass);
        }

        updateUploadNumber();
    });

    dropzone.on('uploadprogress', (file, progress) => {
        const percent = Math.round(progress);
        const fileId = `file-${encodeURIComponent(file.name)}${file.size}${file.lastModified}`;
        const fileItem = document.getElementById(fileId);
        let uploadInfoClone;

        if (fileItem) {
            const progressBar = fileItem.querySelector(uploadProgressSelector);
            if (progressBar) {
                progressBar.style.width = `${percent}%`;
            }
        } else if (uploadInfo) {
            uploadInfoClone = uploadInfo.cloneNode(true);

            const fileNameEl = uploadInfoClone.querySelector(uploadFileNameSelector);
            if (fileNameEl) {
                fileNameEl.textContent = file.name;
            }
            const progressEl = uploadInfoClone.querySelector(uploadProgressSelector);
            if (progressEl) {
                progressEl.style.width = `${percent}%`;
            }
            uploadInfoClone.classList.remove(hiddenClass);
            uploadInfoClone.setAttribute('id', fileId);
            if (uploadInfoContainer) {
                uploadInfoContainer.appendChild(uploadInfoClone);
            }
        }
    });

    dropzone.on('success', (file, response) => {
        const fileId = `file-${encodeURIComponent(file.name)}${file.size}${file.lastModified}`;
        const fileEl = document.getElementById(fileId);
        if (fileEl) {
            fileEl.remove();
        }

        if (response.error) {
            hasErrors = true;
            window.filerShowError(`${file.name}: ${response.error}`);
        }

        submitNum--;
        updateUploadNumber();

        if (submitNum === 0) {
            maxSubmitNum = 1;

            if (uploadWelcome) {
                uploadWelcome.classList.add(hiddenClass);
            }
            if (uploadNumber) {
                uploadNumber.classList.add(hiddenClass);
            }
            if (uploadCanceled) {
                uploadCanceled.classList.add(hiddenClass);
            }
            if (uploadCancel) {
                uploadCancel.classList.add(hiddenClass);
            }
            if (uploadSuccess) {
                uploadSuccess.classList.remove(hiddenClass);
            }

            if (hasErrors) {
                setTimeout(reloadOrdered, 1000);
            } else {
                reloadOrdered();
            }
        }
    });

    dropzone.on('error', (file, errorMessage) => {
        const fileId = `file-${encodeURIComponent(file.name)}${file.size}${file.lastModified}`;
        const fileEl = document.getElementById(fileId);
        if (fileEl) {
            fileEl.remove();
        }

        hasErrors = true;
        window.filerShowError(`${file.name}: ${errorMessage}`);

        submitNum--;
        updateUploadNumber();

        if (submitNum === 0) {
            maxSubmitNum = 1;

            if (uploadWelcome) {
                uploadWelcome.classList.add(hiddenClass);
            }
            if (uploadNumber) {
                uploadNumber.classList.add(hiddenClass);
            }
            if (uploadCanceled) {
                uploadCanceled.classList.add(hiddenClass);
            }
            if (uploadCancel) {
                uploadCancel.classList.add(hiddenClass);
            }
            if (uploadSuccess) {
                uploadSuccess.classList.remove(hiddenClass);
            }

            setTimeout(reloadOrdered, 1000);
        }
    });

    if (uploadCancel) {
        uploadCancel.addEventListener('click', (clickEvent) => {
            clickEvent.preventDefault();
            uploadCancel.classList.add(hiddenClass);
            if (uploadNumber) {
                uploadNumber.classList.add(hiddenClass);
            }
            if (uploadInfoContainer) {
                uploadInfoContainer.classList.add(hiddenClass);
            }
            if (uploadCanceled) {
                uploadCanceled.classList.remove(hiddenClass);
            }

            setTimeout(() => {
                window.location.reload();
            }, 1000);
        });
    }

    if (uploadButtonDisabled && Cl.filerTooltip) {
        Cl.filerTooltip();
    }

    // Fire custom event after scripts have been executed
    document.dispatchEvent(new Event('filer-upload-scripts-executed'));
});
