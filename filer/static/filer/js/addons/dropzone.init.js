// #DROPZONE#
// This script implements the dropzone settings
/* globals Dropzone, django */
'use strict';

// as of Django 2.x we need to check where jQuery is
var djQuery = window.$;

if (django.jQuery) {
    djQuery = django.jQuery;
}

if (Dropzone) {
    Dropzone.autoDiscover = false;
}

/* globals Dropzone, django */
djQuery(function ($) {
    var dropzoneTemplateSelector = '.js-filer-dropzone-template';
    var previewImageSelector = '.js-img-preview';
    var dropzoneSelector = '.js-filer-dropzone';
    var dropzones = $(dropzoneSelector);
    var messageSelector = '.js-filer-dropzone-message';
    var lookupButtonSelector = '.js-related-lookup';
    var progressSelector = '.js-filer-dropzone-progress';
    var previewImageWrapperSelector = '.js-img-wrapper';
    var filerClearerSelector = '.filerClearer';
    var fileChooseSelector = '.js-file-selector';
    var fileIdInputSelector = '.vForeignKeyRawIdAdminField';
    var dragHoverClass = 'dz-drag-hover';
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
        } catch (e) {
            if (window.filerShowError) {
                window.filerShowError(message);
            } else {
                alert(message);
            }
        }
    };

    var createDropzone = function () {
        var dropzone = $(this);
        var dropzoneUrl = dropzone.data('url');
        var inputId = dropzone.find(fileIdInputSelector);
        var isImage = inputId.is('[name="image"]');
        var lookupButton = dropzone.find(lookupButtonSelector);
        var message = dropzone.find(messageSelector);
        var clearButton = dropzone.find(filerClearerSelector);
        var fileChoose = dropzone.find(fileChooseSelector);

        if (this.dropzone) {
            return;
        }

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
                    this.removeAllFiles();
                    clearButton.trigger('click');
                });
                $('img', this.element).on('dragstart', function (event) {
                    event.preventDefault();
                });
                clearButton.on('click', function () {
                    dropzone.removeClass(objectAttachedClass);
                    inputId.trigger('change');
                });
            },
            maxfilesexceeded: function () {
                this.removeAllFiles(true);
            },
            drop: function () {
                this.removeAllFiles(true);
                fileChoose.hide();
                lookupButton.addClass('related-lookup-change');
                message.addClass(hiddenClass);
                dropzone.removeClass(dragHoverClass);
                dropzone.addClass(objectAttachedClass);
            },
            success: function (file, response) {
                $(progressSelector).addClass(hiddenClass);
                if (file && file.status === 'success' && response) {
                    if (response.file_id) {
                        inputId.val(response.file_id);
                        inputId.trigger('change');
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
                        showError(file.name + ': ' + response.error);
                    }
                    this.removeAllFiles(true);
                }

                $('img', this.element).on('dragstart', function (event) {
                    event.preventDefault();
                });
            },
            error: function (file, msg, response) {
                if (response && response.error) {
                    msg += ' ; ' + response.error;
                }
                showError(file.name + ': ' + msg);
                this.removeAllFiles(true);
            },
            reset: function () {
                if (isImage) {
                    $(previewImageWrapperSelector).addClass(hiddenClass);
                    $(previewImageSelector).css({'background-image': 'none'});
                }
                dropzone.removeClass(objectAttachedClass);
                inputId.val('');
                lookupButton.removeClass('related-lookup-change');
                message.removeClass(hiddenClass);
                inputId.trigger('change');
            }
        });
    };

    if (dropzones.length && Dropzone) {
        if (!window.filerDropzoneInitialized) {
            window.filerDropzoneInitialized = true;
            Dropzone.autoDiscover = false;
        }
        dropzones.each(createDropzone);
        // window.__admin_utc_offset__ is used as canary to detect Django 1.8
        // There is no way to feature detect the new behavior implemented in Django 1.9
        if (!window.__admin_utc_offset__) {
            $(document).on('formset:added', function (ev, row) {
                var dropzones = $(row).find(dropzoneSelector);
                dropzones.each(createDropzone);
            });
        } else {
            $('.add-row a').on('click', function () {
                var dropzones = $(dropzoneSelector);
                dropzones.each(createDropzone);
            });
        }
    }
});
