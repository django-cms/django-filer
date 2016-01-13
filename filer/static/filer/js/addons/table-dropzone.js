// #DROPZONE#
// This script implements the dropzone settings
'use strict';

/* globals Dropzone */
(function ($) {
    $(function () {
        var submitNum = 0;
        var maxSubmitNum = 1;
        var dropzoneBase = $('.js-dropzone-base');
        var dropzoneSelector = '.js-dropzone';
        var dropzones;
        var infoMessageClass = 'js-dropzone-info-message';
        var infoMessage = $('.' + infoMessageClass);
        var folderName = $('.js-dropzone-folder-name');
        var uploadInfo = $('.js-dropzone-upload-info');
        var uploadWelcome = $('.js-dropzone-upload-welcome');
        var uploadNumber = $('.js-dropzone-upload-number');
        var uploadFileName = $('.js-dropzone-file-name');
        var uploadProgress = $('.js-dropzone-progress');
        var uploadSuccess = $('.js-dropzone-upload-success');
        var dragHoverClass = 'dz-drag-hover';
        var hiddenClass = 'hidden';
        var hideMessageTimeout;
        var hasErrors = false;
        var baseUrl;
        var baseFolderTitle;

        if (dropzoneBase && dropzoneBase.length) {
            baseUrl = dropzoneBase.data('url');
            baseFolderTitle = dropzoneBase.data('folder-name');

            $('body').data('url', baseUrl).data('folder-name', baseFolderTitle).addClass('js-dropzone');
        }

        dropzones = $(dropzoneSelector);

        if (dropzones.length && Dropzone) {
            Dropzone.autoDiscover = false;
            dropzones.each(function () {
                var dropzone = $(this);
                var dropzoneUrl = $(this).data('url');
                new Dropzone(this, {
                    url: dropzoneUrl,
                    paramName: 'file',
                    maxFiles: 100,
                    previewTemplate: '<div></div>',
                    clickable: false,
                    addRemoveLinks: false,
                    addedfile: function () {
                        submitNum++;

                        if (maxSubmitNum < submitNum) {
                            maxSubmitNum = submitNum;
                        }
                    },
                    maxfilesexceeded: function (file) {
                        this.removeAllFiles();
                        this.addFile(file);
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
                    drop: function () {
                        dropzones.removeClass('reset-hover');
                        clearTimeout(hideMessageTimeout);
                        infoMessage.removeClass(hiddenClass);
                        dropzones.removeClass(dragHoverClass);
                    },
                    sending: function (file) {
                        uploadWelcome.addClass(hiddenClass);
                        uploadFileName.text(file.name);
                        uploadProgress.width(0);
                        uploadInfo.removeClass(hiddenClass);
                    },
                    uploadprogress: function (file, progress) {
                        uploadProgress.width(progress + '%');
                        uploadNumber.text(maxSubmitNum - submitNum + 1 + '/' + maxSubmitNum);
                    },
                    complete: function () {
                        submitNum--;
                    },
                    queuecomplete: function () {
                        maxSubmitNum = 1;

                        uploadInfo.addClass(hiddenClass);
                        uploadSuccess.removeClass(hiddenClass);
                        if (hasErrors) {
                            setTimeout(function () {
                                window.location.reload();
                            }, 3000);
                        } else {
                            window.location.reload();
                        }
                    },
                    error: function (file) {
                        hasErrors = true;
                        window.showError(file.name + ': ' + file.xhr.statusText);
                    }
                });
            });
        }
    });
})(jQuery);
