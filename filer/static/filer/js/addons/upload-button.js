// #UPLOAD BUTTON#
// This script implements the upload button logic
'use strict';

// as of Django 2.x we need to check where jQuery is
var djQuery = window.$;

if (django.jQuery) {
    djQuery = django.jQuery;
}

/* globals qq, Cl, django */
(function ($) {
    $(function () {
        var submitNum = 0;
        var maxSubmitNum = 1;
        var uploadButton = $('.js-upload-button');
        var uploadButtonDisabled = $('.js-upload-button-disabled');
        var uploadUrl = uploadButton.data('url');
        var uploadWelcome = $('.js-filer-dropzone-upload-welcome');
        var uploadInfoContainer = $('.js-filer-dropzone-upload-info-container');
        var uploadInfo = $('.js-filer-dropzone-upload-info');
        var uploadNumber = $('.js-filer-dropzone-upload-number');
        var uploadFileNameSelector = '.js-filer-dropzone-file-name';
        var uploadProgressSelector = '.js-filer-dropzone-progress';
        var uploadSuccess = $('.js-filer-dropzone-upload-success');
        var uploadCanceled = $('.js-filer-dropzone-upload-canceled');
        var uploadCancel = $('.js-filer-dropzone-cancel');
        var infoMessage = $('.js-filer-dropzone-info-message');
        var hiddenClass = 'hidden';
        var maxUploaderConnections = uploadButton.data('max-uploader-connections') || 3;
        var hasErrors = false;
        var updateUploadNumber = function () {
            uploadNumber.text(maxSubmitNum - submitNum + '/' + maxSubmitNum);
        };
        var removeButton = function () {
            uploadButton.remove();
        };
        // utility
        var updateQuery = function (uri, key, value) {
            var re = new RegExp('([?&])' + key + '=.*?(&|$)', 'i');
            var separator = uri.indexOf('?') !== -1 ? '&' : '?';
            var hash = window.location.hash;
            uri = uri.replace(/#.*$/, '');
            if (uri.match(re)) {
                return uri.replace(re, '$1' + key + '=' + value + '$2') + hash;
            } else {
                return uri + separator + key + '=' + value + hash;
            }
        };
        var reloadOrdered = function () {
            var uri = window.location.toString();
            window.location.replace(updateQuery(uri, 'order_by', '-modified_at'));
        };

        Cl.mediator.subscribe('filer-upload-in-progress', removeButton);

        new qq.FileUploaderBasic({
            action: uploadUrl,
            button: uploadButton[0],
            maxConnections: maxUploaderConnections,
            onSubmit: function (id) {
                Cl.mediator.remove('filer-upload-in-progress', removeButton);
                Cl.mediator.publish('filer-upload-in-progress');
                submitNum++;

                maxSubmitNum = id + 1;

                infoMessage.removeClass(hiddenClass);
                uploadWelcome.addClass(hiddenClass);
                uploadSuccess.addClass(hiddenClass);
                uploadInfoContainer.removeClass(hiddenClass);
                uploadCancel.removeClass(hiddenClass);
                uploadCanceled.addClass(hiddenClass);

                updateUploadNumber();
            },
            onProgress: function (id, fileName, loaded, total) {
                var percent = Math.round(loaded / total * 100);
                var fileItem = $('#file-' + id);
                var uploadInfoClone;

                if (fileItem.length) {
                    fileItem.find(uploadProgressSelector).width(percent + '%');
                } else {
                    uploadInfoClone = uploadInfo.clone();

                    uploadInfoClone.find(uploadFileNameSelector).text(fileName);
                    uploadInfoClone.find(uploadProgressSelector).width(percent);
                    uploadInfoClone.removeClass(hiddenClass)
                        .attr('id', 'file-' + id)
                        .appendTo(uploadInfoContainer);
                }
            },
            onComplete: function (id, fileName, responseJSON) {
                var file = responseJSON;

                $('#file-' + id).remove();

                if (file.error) {
                    hasErrors = true;
                    window.filerShowError(fileName + ': ' + file.error);
                }

                submitNum--;
                updateUploadNumber();

                if (submitNum === 0) {
                    maxSubmitNum = 1;

                    uploadWelcome.addClass(hiddenClass);
                    uploadNumber.addClass(hiddenClass);
                    uploadCanceled.addClass(hiddenClass);
                    uploadCancel.addClass(hiddenClass);
                    uploadSuccess.removeClass(hiddenClass);

                    if (hasErrors) {
                        setTimeout(reloadOrdered, 1000);
                    } else {
                        reloadOrdered();
                    }
                }
            }
        });

        uploadCancel.on('click', function (clickEvent) {
            clickEvent.preventDefault();
            uploadCancel.addClass(hiddenClass);
            uploadNumber.addClass(hiddenClass);
            uploadInfoContainer.addClass(hiddenClass);
            uploadCanceled.removeClass(hiddenClass);

            setTimeout(function () {
                window.location.reload();
            }, 1000);
        });

        if (uploadButtonDisabled.length) {
            Cl.filerTooltip($);
        }
    });
})(djQuery);
