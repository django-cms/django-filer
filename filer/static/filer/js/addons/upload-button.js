// #UPLOAD BUTTON#
// This script implements the upload button logic
'use strict';

/* globals qq */
(function ($) {
    $(function () {
        var submitNum = 0;
        var maxSubmitNum = 1;
        var uploadButton = $('.js-upload-button');
        var uploadUrl = uploadButton.data('url');
        var uploadWelcome = $('.js-dropzone-upload-welcome');
        var uploadSuccess = $('.js-dropzone-upload-success');
        var uploadInfo = $('.js-dropzone-upload-info');
        var uploadFileName = $('.js-dropzone-file-name');
        var uploadProgress = $('.js-dropzone-progress');
        var uploadNumber = $('.js-dropzone-upload-number');
        var infoMessage = $('.js-dropzone-info-message');
        var hiddenClass = 'hidden';
        var hasErrors = false;

        new qq.FileUploaderBasic({
            action: uploadUrl,
            button: uploadButton[0],
            onSubmit: function () {
                submitNum++;

                if (maxSubmitNum < submitNum) {
                    maxSubmitNum = submitNum;
                }
            },
            onProgress: function (id, fileName, loaded, total) {
                var percent = Math.round(loaded / total * 100);

                uploadWelcome.addClass(hiddenClass);
                uploadSuccess.addClass(hiddenClass);
                uploadInfo.removeClass(hiddenClass);
                uploadNumber.text(maxSubmitNum - submitNum + 1 + '/' + maxSubmitNum);
                uploadFileName.removeClass(hiddenClass).text(fileName);
                uploadProgress.removeClass(hiddenClass).width(percent + '%');
                infoMessage.removeClass(hiddenClass);
            },
            onComplete: function (id, fileName, responseJSON) {
                var file = responseJSON;

                if (file.error) {
                    hasErrors = true;
                    window.showError(fileName + ': ' + file.error);
                }

                submitNum--;

                if (submitNum === 0) {
                    maxSubmitNum = 1;

                    uploadWelcome.addClass(hiddenClass);
                    uploadSuccess.removeClass(hiddenClass);
                    uploadNumber.addClass(hiddenClass);
                    uploadFileName.addClass(hiddenClass);
                    uploadProgress.addClass(hiddenClass).width(0);
                    infoMessage.removeClass(hiddenClass);

                    if (hasErrors) {
                        setTimeout(function () {
                            window.location.reload();
                        }, 3000);
                    } else {
                        window.location.reload();
                    }
                }
            }
        });
    });
})(jQuery);
