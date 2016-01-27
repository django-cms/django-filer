// #DROPZONE#
// This script implements the dropzone settings
'use strict';

/* global Dropzone */
(function ($) {
    $(function () {
        var dropzoneTemplateSelector = '.js-filer-dropzone-template';
        var previewImageSelector = '.js-img-preview';
        var dropzoneSelector = '.js-filer-dropzone';
        var messageSelector = '.js-filer-dropzone-message';
        var lookupButtonSelector = '.js-related-lookup';
        var progressSelector = '.js-filer-dropzone-progress';
        var previewImageWrapperSelector = '.js-img-wrapper';
        var filerClearerSelector = '.filerClearer';
        var fileChooseSelector = '.js-file-selector';
        var dropzones = $(dropzoneSelector);
        var fileIdInputSelector = '.vForeignKeyRawIdAdminField';
        var hiddenClass = 'hidden';
        var mobileClass = 'filer-dropzone-mobile';
        var objectAttachedClass = 'js-object-attached';
        // var dataMaxFileSize = 'max-file-size';
        var minWidth = 500;
        var checkMinWidth = function (element) {
            element.toggleClass(mobileClass, element.width() < minWidth);
        };
        var showError = function (message) {
            try {
                window.parent.CMS.API.Messages.open({
                    message: message
                });
            } catch (errorText) {
                console.log(errorText);
            }
        };

        if (dropzones.length && Dropzone) {
            if (!window.filerDropzoneInitialized) {
                window.filerDropzoneInitialized = true;
                Dropzone.autoDiscover = false;
            }

            dropzones.filter(function () {
                return !this.dropzone;
            }).each(function () {
                var dropzone = $(this);
                var dropzoneUrl = dropzone.data('url');
                var inputId = dropzone.find(fileIdInputSelector);
                var isImage = inputId.is('[name="image"]');
                var lookupButton = dropzone.find(lookupButtonSelector);
                var message = dropzone.find(messageSelector);
                var clearButton = dropzone.find(filerClearerSelector);
                var fileChoose = dropzone.find(fileChooseSelector);

                $(window).on('resize', function () {
                    checkMinWidth(dropzone);
                });

                new Dropzone(this, {
                    url: dropzoneUrl,
                    paramName: 'file',
                    maxFiles: 1,
                    // for now disabled as we don't have the correct file size limit
                    // maxFilesize: dropzone.data(dataMaxFileSize) || 20, // MB
                    previewTemplate: $(dropzoneTemplateSelector).html(),
                    clickable: false,
                    addRemoveLinks: false,
                    init: function () {
                        checkMinWidth(dropzone);
                        this.on('removedfile', function () {
                            fileChoose.show();
                            dropzone.removeClass(objectAttachedClass);
                            this.removeAllFiles(true);
                            clearButton.trigger('click');
                        });
                        $('img', this.element).on('dragstart', function (event) {
                            event.preventDefault();
                        });
                        clearButton.on('click', function () {
                            dropzone.removeClass(objectAttachedClass);
                        });
                    },
                    maxfilesexceeded: function () {
                        this.removeAllFiles(true);
                    },
                    drop: function () {
                        this.removeAllFiles(true);
                        fileChoose.hide();
                        lookupButton.addClass(hiddenClass);
                        message.addClass(hiddenClass);
                        dropzone.removeClass('dz-drag-hover');
                        dropzone.addClass(objectAttachedClass);
                    },
                    success: function (file, response) {
                        dropzone.find(progressSelector).addClass(hiddenClass);

                        if (file && file.status === 'success' && response) {
                            if (response.file_id) {
                                inputId.val(response.file_id);
                            }
                            if (response.thumbnail_180) {
                                if (isImage) {
                                    $(previewImageSelector).css({
                                        'background-image': 'url(' + response.thumbnail_180 + ')'
                                    });
                                    $(previewImageWrapperSelector).removeClass(hiddenClass);
                                }
                            }
                        } else {
                            if (response && response.error) {
                                window.showError(file.name + ': ' + response.error);
                            }
                            this.removeAllFiles(true);
                        }

                        $('img', this.element).on('dragstart', function (event) {
                            event.preventDefault();
                        });
                    },
                    error: function (file, response) {
                        showError(file.name + ': ' + response.error);
                        this.removeAllFiles(true);
                    },
                    reset: function () {
                        if (isImage) {
                            $(previewImageWrapperSelector).addClass(hiddenClass);
                            $(previewImageSelector).css({'background-image': 'none'});
                        }
                        dropzone.removeClass(objectAttachedClass);
                        inputId.val('');
                        lookupButton.removeClass(hiddenClass);
                        message.removeClass(hiddenClass);
                    }
                });
            });
        }
    });
})(jQuery);
