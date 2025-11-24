// #DROPZONE#
// This script implements the dropzone settings
'use strict';

import Dropzone from 'dropzone';


/* globals Cl */
document.addEventListener('DOMContentLoaded', () => {
    let submitNum = 0;
    let maxSubmitNum = 0;
    const dropzoneInstances = [];
    const dropzoneBase = document.querySelector('.js-filer-dropzone-base');
    const dropzoneSelector = '.js-filer-dropzone';
    let dropzones;
    const infoMessageClass = 'js-filer-dropzone-info-message';
    const infoMessage = document.querySelector(`.${infoMessageClass}`);
    const folderName = document.querySelector('.js-filer-dropzone-folder-name');
    const uploadInfoContainer = document.querySelector('.js-filer-dropzone-upload-info-container');
    const uploadInfo = document.querySelector('.js-filer-dropzone-upload-info');
    const uploadWelcome = document.querySelector('.js-filer-dropzone-upload-welcome');
    const uploadNumber = document.querySelector('.js-filer-dropzone-upload-number');
    const uploadCount = document.querySelector('.js-filer-upload-count');
    const uploadText = document.querySelector('.js-filer-upload-text');
    const uploadFileNameSelector = '.js-filer-dropzone-file-name';
    const uploadProgressSelector = '.js-filer-dropzone-progress';
    const uploadSuccess = document.querySelector('.js-filer-dropzone-upload-success');
    const uploadCanceled = document.querySelector('.js-filer-dropzone-upload-canceled');
    const cancelUpload = document.querySelector('.js-filer-dropzone-cancel');
    const dragHoverClass = 'dz-drag-hover';
    const dataUploaderConnections = 'max-uploader-connections';
    const dragHoverBorder = document.querySelector('.drag-hover-border');
    const hiddenClass = 'hidden';
    let hideMessageTimeout;
    let hasErrors = false;
    let baseUrl;
    let baseFolderTitle;

    const updateUploadNumber = () => {
        if (uploadNumber) {
            uploadNumber.textContent = `${maxSubmitNum - submitNum}/${maxSubmitNum}`;
        }
        if (uploadText) {
            uploadText.classList.remove('hidden');
        }
        if (uploadCount) {
            uploadCount.classList.remove('hidden');
        }
    };

    const destroyDropzones = () => {
        dropzoneInstances.forEach((instance) => {
            instance.destroy();
        });
    };

    const getElementByFile = (file, url) => {
        return document.getElementById(
            `file-${encodeURIComponent(file.name)}${file.size}${file.lastModified}${url}`
        );
    };

    if (dropzoneBase) {
        baseUrl = dropzoneBase.dataset.url;
        baseFolderTitle = dropzoneBase.dataset.folderName;

        const body = document.body;
        body.dataset.url = baseUrl;
        body.dataset.folderName = baseFolderTitle;
        body.dataset.maxFiles = dropzoneBase.dataset.maxFiles;
        body.dataset.maxFilesize = dropzoneBase.dataset.maxFiles;
        body.classList.add('js-filer-dropzone');
    }

    Cl.mediator.subscribe('filer-upload-in-progress', destroyDropzones);

    dropzones = document.querySelectorAll(dropzoneSelector);

    if (dropzones.length && Dropzone) {
        Dropzone.autoDiscover = false;
        dropzones.forEach((dropzoneElement) => {
            const dropzoneUrl = dropzoneElement.dataset.url;
            const dropzoneInstance = new Dropzone(dropzoneElement, {
                url: dropzoneUrl,
                paramName: 'file',
                maxFiles: parseInt(dropzoneElement.dataset.maxFiles) || 100,
                maxFilesize: parseInt(dropzoneElement.dataset.maxFilesize),  // no default
                previewTemplate: '<div></div>',
                clickable: false,
                addRemoveLinks: false,
                parallelUploads: dropzoneElement.dataset[dataUploaderConnections] || 3,
                accept: (file, done) => {
                    let uploadInfoClone;

                    Cl.mediator.remove('filer-upload-in-progress', destroyDropzones);
                    Cl.mediator.publish('filer-upload-in-progress');

                    clearTimeout(hideMessageTimeout);
                    clearTimeout(hideMessageTimeout);
                    if (uploadWelcome) {
                        uploadWelcome.classList.add(hiddenClass);
                    }
                    if (cancelUpload) {
                        cancelUpload.classList.remove(hiddenClass);
                    }

                    if (getElementByFile(file, dropzoneUrl)) {
                        done('duplicate');
                    } else {
                        uploadInfoClone = uploadInfo.cloneNode(true);

                        const fileNameEl = uploadInfoClone.querySelector(uploadFileNameSelector);
                        if (fileNameEl) {
                            fileNameEl.textContent = file.name;
                        }
                        const progressEl = uploadInfoClone.querySelector(uploadProgressSelector);
                        if (progressEl) {
                            progressEl.style.width = '0';
                        }
                        uploadInfoClone.setAttribute(
                            'id',
                            `file-${encodeURIComponent(file.name)}${file.size}${file.lastModified}${dropzoneUrl}`
                        );
                        if (uploadInfoContainer) {
                            uploadInfoContainer.appendChild(uploadInfoClone);
                        }

                        submitNum++;
                        maxSubmitNum++;
                        updateUploadNumber();
                        done();
                    }

                    dropzones.forEach((dz) => dz.classList.remove('reset-hover'));
                    if (infoMessage) {
                        infoMessage.classList.remove(hiddenClass);
                    }
                    dropzones.forEach((dz) => dz.classList.remove(dragHoverClass));
                },
                dragover: (dragEvent) => {
                    const target = dragEvent.target.closest(dropzoneSelector);
                    const folderTitle = target?.dataset.folderName;
                    const dropzoneFolder = dropzoneElement.classList.contains('js-filer-dropzone-folder');
                    const dropzoneBoundingRect = dropzoneElement.getBoundingClientRect();
                    const borderStyle = dragHoverBorder ? window.getComputedStyle(dragHoverBorder) : null;
                    const topBorderSize = borderStyle ? borderStyle.borderTopWidth : '0px';
                    const leftBorderSize = borderStyle ? borderStyle.borderLeftWidth : '0px';
                    const dropzonePosition = {
                        top: `${dropzoneBoundingRect.top}px`,
                        bottom: `${dropzoneBoundingRect.bottom}px`,
                        left: `${dropzoneBoundingRect.left}px`,
                        right: `${dropzoneBoundingRect.right}px`,
                        width: `${dropzoneBoundingRect.width - parseInt(leftBorderSize, 10) * 2}px`,
                        height: `${dropzoneBoundingRect.height - parseInt(topBorderSize, 10) * 2}px`,
                        display: 'block'
                    };
                    if (dropzoneFolder && dragHoverBorder) {
                        Object.assign(dragHoverBorder.style, dropzonePosition);
                    }

                    dropzones.forEach((dz) => dz.classList.add('reset-hover'));
                    if (uploadSuccess) {
                        uploadSuccess.classList.add(hiddenClass);
                    }
                    if (infoMessage) {
                        infoMessage.classList.remove(hiddenClass);
                    }
                    dropzoneElement.classList.add(dragHoverClass);
                    dropzoneElement.classList.remove('reset-hover');

                    if (folderName && folderTitle) {
                        folderName.textContent = folderTitle;
                    }
                },
                dragend: () => {
                    clearTimeout(hideMessageTimeout);
                    hideMessageTimeout = setTimeout(() => {
                        if (infoMessage) {
                            infoMessage.classList.add(hiddenClass);
                        }
                    }, 1000);

                    if (infoMessage) {
                        infoMessage.classList.remove(hiddenClass);
                    }
                    dropzones.forEach((dz) => dz.classList.remove(dragHoverClass));
                    if (dragHoverBorder) {
                        Object.assign(dragHoverBorder.style, { top: '0', bottom: '0', width: '0', height: '0' });
                    }
                },
                dragleave: () => {
                    clearTimeout(hideMessageTimeout);
                    hideMessageTimeout = setTimeout(() => {
                        if (infoMessage) {
                            infoMessage.classList.add(hiddenClass);
                        }
                    }, 1000);

                    if (infoMessage) {
                        infoMessage.classList.remove(hiddenClass);
                    }
                    dropzones.forEach((dz) => dz.classList.remove(dragHoverClass));
                    if (dragHoverBorder) {
                        Object.assign(dragHoverBorder.style, { top: '0', bottom: '0', width: '0', height: '0' });
                    }
                },
                sending: (file) => {
                    const fileEl = getElementByFile(file, dropzoneUrl);
                    if (fileEl) {
                        fileEl.classList.remove(hiddenClass);
                    }
                },
                uploadprogress: (file, progress) => {
                    const fileEl = getElementByFile(file, dropzoneUrl);
                    if (fileEl) {
                        const progressEl = fileEl.querySelector(uploadProgressSelector);
                        if (progressEl) {
                            progressEl.style.width = `${progress}%`;
                        }
                    }
                },
                success: (file) => {
                    submitNum--;
                    updateUploadNumber();
                    const fileEl = getElementByFile(file, dropzoneUrl);
                    if (fileEl) {
                        fileEl.remove();
                    }
                },
                queuecomplete: () => {
                    if (submitNum !== 0) {
                        return;
                    }

                    updateUploadNumber();

                    if (cancelUpload) {
                        cancelUpload.classList.add(hiddenClass);
                    }
                    if (uploadInfo) {
                        uploadInfo.classList.add(hiddenClass);
                    }

                    if (hasErrors) {
                        if (uploadNumber) {
                            uploadNumber.classList.add(hiddenClass);
                        }
                        setTimeout(() => {
                            window.location.reload();
                        }, 1000);
                    } else {
                        if (uploadSuccess) {
                            uploadSuccess.classList.remove(hiddenClass);
                        }
                        window.location.reload();
                    }
                },
                error: (file, error) => {
                    updateUploadNumber();
                    if (error === 'duplicate') {
                        return;
                    }
                    hasErrors = true;
                    if (window.filerShowError) {
                        window.filerShowError(`${file.name}: ${error.message}`);
                    }
                }
            });
            dropzoneInstances.push(dropzoneInstance);
            if (cancelUpload) {
                cancelUpload.addEventListener('click', (clickEvent) => {
                    clickEvent.preventDefault();
                    cancelUpload.classList.add(hiddenClass);
                    if (uploadCanceled) {
                        uploadCanceled.classList.remove(hiddenClass);
                    }
                    dropzoneInstance.removeAllFiles(true);
                });
            }
        });
    }
});
