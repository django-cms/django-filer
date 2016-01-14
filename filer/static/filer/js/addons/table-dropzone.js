// #DROPZONE#
// This script implements the dropzone settings
'use strict';

/* globals Dropzone, Cl */
(function ($) {
    $(function () {
        var submitNum = 0;
        var maxSubmitNum = 1;
        var dropzoneInstances = [];
        var dropzoneBase = $('.js-filer-dropzone-base');
        var dropzoneSelector = '.js-filer-dropzone';
        var dropzones;
        var infoMessageClass = 'js-filer-dropzone-info-message';
        var infoMessage = $('.' + infoMessageClass);
        var folderName = $('.js-filer-dropzone-folder-name');
        var uploadInfoContainer = $('.js-filer-dropzone-upload-info-container');
        var uploadInfo = $('.js-filer-dropzone-upload-info');
        var uploadWelcome = $('.js-filer-dropzone-upload-welcome');
        var uploadNumber = $('.js-filer-dropzone-upload-number');
        var uploadFileNameSelector = '.js-filer-dropzone-file-name';
        var uploadProgressSelector = '.js-filer-dropzone-progress';
        var uploadSuccess = $('.js-filer-dropzone-upload-success');
        var uploadCanceled = $('.js-filer-dropzone-upload-canceled');
        var cancelUpload = $('.js-filer-dropzone-cancel');
        var dragHoverClass = 'dz-drag-hover';
        var dataUploaderConnections = 'max-uploader-connections';
        var hiddenClass = 'hidden';
        var hideMessageTimeout;
        var hasErrors = false;
        var baseUrl;
        var baseFolderTitle;
        var updateUploadNumber = function () {
            uploadNumber.text(maxSubmitNum - submitNum + '/' + maxSubmitNum);
        };
        var destroyDropzones = function () {
            $.each(dropzoneInstances, function (index) {
                dropzoneInstances[index].destroy();
            });
        };

        if (dropzoneBase && dropzoneBase.length) {
            baseUrl = dropzoneBase.data('url');
            baseFolderTitle = dropzoneBase.data('folder-name');

            $('body').data('url', baseUrl).data('folder-name', baseFolderTitle).addClass('js-filer-dropzone');
        }

        Cl.mediator.subscribe('filer-upload-in-progress', destroyDropzones);

        dropzones = $(dropzoneSelector);

        if (dropzones.length && Dropzone) {
            Dropzone.autoDiscover = false;
            dropzones.each(function () {
                var dropzone = $(this);
                var dropzoneUrl = $(this).data('url');
                var dropzoneInstance = new Dropzone(this, {
                    url: dropzoneUrl,
                    paramName: 'file',
                    maxFiles: 100,
                    previewTemplate: '<div></div>',
                    clickable: false,
                    addRemoveLinks: false,
                    parallelUploads: dropzone.data(dataUploaderConnections) || 3,
                    addedfile: function () {
                        Cl.mediator.remove('filer-upload-in-progress', destroyDropzones);
                        Cl.mediator.publish('filer-upload-in-progress');
                        submitNum++;

                        if (submitNum > maxSubmitNum) {
                            maxSubmitNum = submitNum;
                        }

                        cancelUpload.removeClass(hiddenClass);
                        updateUploadNumber(this.files);

                        dropzones.removeClass('reset-hover');
                        clearTimeout(hideMessageTimeout);
                        infoMessage.removeClass(hiddenClass);
                        dropzones.removeClass(dragHoverClass);
                    },
                    dragover: function (dragEvent) {
                        var folderTitle = $(dragEvent.target).closest(dropzoneSelector).data('folder-name');
                        $(dropzones).addClass('reset-hover');
                        uploadSuccess.addClass(hiddenClass);
                        infoMessage.removeClass(hiddenClass);
                        dropzone.addClass(dragHoverClass).removeClass('reset-hover');

                        folderName.text(folderTitle);
                    },
                    dragleave: function () {
                        clearTimeout(hideMessageTimeout);
                        hideMessageTimeout = setTimeout(function () {
                            infoMessage.addClass(hiddenClass);
                        }, 1000);

                        infoMessage.removeClass(hiddenClass);
                        dropzones.removeClass(dragHoverClass);
                    },
                    sending: function (file) {
                        var uploadInfoClone = uploadInfo.clone();

                        uploadWelcome.addClass(hiddenClass);

                        uploadInfoClone.find(uploadFileNameSelector).text(file.name);
                        uploadInfoClone.find(uploadProgressSelector).width(0);
                        uploadInfoClone.removeClass(hiddenClass)
                            .attr('id', 'file-' + file.size + file.lastModified)
                            .appendTo(uploadInfoContainer);
                    },
                    uploadprogress: function (file, progress) {
                        $('#file-' + file.size + file.lastModified).find(uploadProgressSelector)
                            .width(progress + '%');
                    },
                    complete: function (file) {
                        $('#file-' + file.size + file.lastModified).remove();
                        submitNum--;
                        updateUploadNumber(this.files);
                    },
                    queuecomplete: function () {
                        if (submitNum !== 0) {
                            return;
                        }

                        updateUploadNumber(this.files);

                        cancelUpload.addClass(hiddenClass);
                        uploadInfo.addClass(hiddenClass);

                        if (hasErrors) {
                            uploadNumber.addClass(hiddenClass);
                            setTimeout(function () {
                                window.location.reload();
                            }, 1000);
                        } else {
                            uploadSuccess.removeClass(hiddenClass);
                            window.location.reload();
                        }
                    },
                    error: function (file) {
                        hasErrors = true;
                        window.showError(file.name + ': ' + file.xhr.statusText);
                    }
                });
                cancelUpload.on('click', function (clickEvent) {
                    clickEvent.preventDefault();
                    cancelUpload.addClass(hiddenClass);
                    uploadCanceled.removeClass(hiddenClass);
                    dropzoneInstance.removeAllFiles(true);
                });
                dropzoneInstances.push(dropzoneInstance);
            });
        }
    });
})(jQuery);
