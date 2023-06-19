// #DROPZONE#
// This script implements the dropzone settings
'use strict';

// as of Django 2.x we need to check where jQuery is
var djQuery = window.$;

if (django.jQuery) {
    djQuery = django.jQuery;
}

/* globals Dropzone, Cl, django */
(function ($) {
    $(function () {
        var submitNum = 0;
        var maxSubmitNum = 0;
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
        var uploadCount = $('.js-filer-upload-count');
        var uploadText = $('.js-filer-upload-text');
        var uploadFileNameSelector = '.js-filer-dropzone-file-name';
        var uploadProgressSelector = '.js-filer-dropzone-progress';
        var uploadSuccess = $('.js-filer-dropzone-upload-success');
        var uploadCanceled = $('.js-filer-dropzone-upload-canceled');
        var cancelUpload = $('.js-filer-dropzone-cancel');
        var dragHoverClass = 'dz-drag-hover';
        var dataUploaderConnections = 'max-uploader-connections';
        var dragHoverBorder = $('.drag-hover-border');
        // var dataMaxFileSize = 'max-file-size';
        var hiddenClass = 'hidden';
        var hideMessageTimeout;
        var hasErrors = false;
        var baseUrl;
        var baseFolderTitle;
        var updateUploadNumber = function () {
            uploadNumber.text(maxSubmitNum - submitNum + '/' + maxSubmitNum);
            uploadText.removeClass('hidden');
            uploadCount.removeClass('hidden');
        };
        var destroyDropzones = function () {
            $.each(dropzoneInstances, function (index) {
                dropzoneInstances[index].destroy();
            });
        };
        var getElementByFile = function (file, url) {
            return $(document.getElementById(
                'file-' +
                encodeURIComponent(file.name) +
                file.size +
                file.lastModified +
                url
            ));
        };

        if (dropzoneBase && dropzoneBase.length) {
            baseUrl = dropzoneBase.data('url');
            baseFolderTitle = dropzoneBase.data('folder-name');

            $('body')
                .data('url', baseUrl)
                .data('folder-name', baseFolderTitle)
                .data('max-files', dropzoneBase.data('max-files'))
                .data('max-filesize', dropzoneBase.data('max-files'))
                .addClass('js-filer-dropzone');
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
                    maxFiles: parseInt(dropzone.data('max-files')) || 100,
                    maxFilesize: parseInt(dropzone.data('max-filesize')),  // no default
                    previewTemplate: '<div></div>',
                    clickable: false,
                    addRemoveLinks: false,
                    parallelUploads: dropzone.data(dataUploaderConnections) || 3,
                    accept: function (file, done) {
                        var uploadInfoClone;

                        Cl.mediator.remove('filer-upload-in-progress', destroyDropzones);
                        Cl.mediator.publish('filer-upload-in-progress');

                        clearTimeout(hideMessageTimeout);
                        uploadWelcome.addClass(hiddenClass);
                        cancelUpload.removeClass(hiddenClass);

                        if (getElementByFile(file, dropzoneUrl).length) {
                            done('duplicate');
                        } else {
                            uploadInfoClone = uploadInfo.clone();

                            uploadInfoClone.find(uploadFileNameSelector).text(file.name);
                            uploadInfoClone.find(uploadProgressSelector).width(0);
                            uploadInfoClone
                                .attr(
                                    'id',
                                    'file-' +
                                        encodeURIComponent(file.name) +
                                        file.size +
                                        file.lastModified +
                                        dropzoneUrl
                                )
                                .appendTo(uploadInfoContainer);

                            submitNum++;
                            maxSubmitNum++;
                            updateUploadNumber();
                            done();
                        }

                        dropzones.removeClass('reset-hover');
                        infoMessage.removeClass(hiddenClass);
                        dropzones.removeClass(dragHoverClass);
                    },
                    dragover: function (dragEvent) {
                        var folderTitle = $(dragEvent.target).closest(dropzoneSelector).data('folder-name');
                        var dropzoneFolder = dropzone.hasClass('js-filer-dropzone-folder');
                        var dropzoneBoundingRect = dropzone[0].getBoundingClientRect();
                        var topBorderSize = $('.drag-hover-border').css('border-top-width');
                        var leftBorderSize = $('.drag-hover-border').css('border-left-width');
                        var dropzonePosition = {
                            top: dropzoneBoundingRect.top,
                            bottom: dropzoneBoundingRect.bottom,
                            left: dropzoneBoundingRect.left,
                            right: dropzoneBoundingRect.right,
                            width: dropzoneBoundingRect.width - parseInt(leftBorderSize, 10) * 2,
                            height: dropzoneBoundingRect.height - parseInt(topBorderSize, 10) * 2,
                            display: 'block'
                        };
                        if (dropzoneFolder) {
                            dragHoverBorder.css(dropzonePosition);
                        }

                        $(dropzones).addClass('reset-hover');
                        uploadSuccess.addClass(hiddenClass);
                        infoMessage.removeClass(hiddenClass);
                        dropzone.addClass(dragHoverClass).removeClass('reset-hover');

                        folderName.text(folderTitle);
                    },
                    dragend: function () {
                        clearTimeout(hideMessageTimeout);
                        hideMessageTimeout = setTimeout(function () {
                            infoMessage.addClass(hiddenClass);
                        }, 1000);

                        infoMessage.removeClass(hiddenClass);
                        dropzones.removeClass(dragHoverClass);
                        dragHoverBorder.css({ top: 0, bottom: 0, width: 0, height: 0 });
                    },
                    dragleave: function () {
                        clearTimeout(hideMessageTimeout);
                        hideMessageTimeout = setTimeout(function () {
                            infoMessage.addClass(hiddenClass);
                        }, 1000);

                        infoMessage.removeClass(hiddenClass);
                        dropzones.removeClass(dragHoverClass);
                        dragHoverBorder.css({ top: 0, bottom: 0, width: 0, height: 0 });

                    },
                    sending: function (file) {
                        getElementByFile(file, dropzoneUrl).removeClass(hiddenClass);
                    },
                    uploadprogress: function (file, progress) {
                        getElementByFile(file, dropzoneUrl).find(uploadProgressSelector).width(progress + '%');
                    },
                    success: function (file) {
                        submitNum--;
                        updateUploadNumber();
                        getElementByFile(file, dropzoneUrl).remove();
                    },
                    queuecomplete: function () {
                        if (submitNum !== 0) {
                            return;
                        }

                        updateUploadNumber();

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
                    error: function (file, error) {
                        updateUploadNumber();
                        if (error === 'duplicate') {
                            return;
                        }
                        hasErrors = true;
                        if (window.filerShowError) {
                            window.filerShowError(file.name + ': ' + error.message);
                        }
                    }
                });
                dropzoneInstances.push(dropzoneInstance);
                cancelUpload.on('click', function (clickEvent) {
                    clickEvent.preventDefault();
                    cancelUpload.addClass(hiddenClass);
                    uploadCanceled.removeClass(hiddenClass);
                    dropzoneInstance.removeAllFiles(true);
                });
            });
        }
    });
})(djQuery);
