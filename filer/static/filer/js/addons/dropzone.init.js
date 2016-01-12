// #DROPZONE#
// This script implements the dropzone settings
'use strict';

if (Dropzone) {
    Dropzone.autoDiscover = false;
}


/* global Dropzone, django */
django.jQuery(function ($) {
    var dropzoneTemplateSelector = '.js-dropzone-template';
    var previewImageSelector = '.js-img-preview';
    var dropzoneSelector = '.js-dropzone';
    var messageSelector = '.js-dropzone-message';
    var lookupButtonSelector = '.js-related-lookup';
    var progressSelector = '.js-dropzone-progress';
    var previewImageWrapperSelector = '.js-img-wrapper';
    var filerClearerSelector = '.filerClearer';
    var fileChooseSelector = '.js-file-selector';
    var fileIdInputSelector = '.vForeignKeyRawIdAdminField';
    var hiddenClass = 'hidden';
    var mobileClass = 'dropzone-mobile';
    var objectAttachedClass = 'js-object-attached';
    var minWidth = 500;
    var checkMinWidth = function () {
        this.toggleClass(mobileClass, this.width() < minWidth);
    };


    var create_dropzone = function () {
        var dropzone = $(this);
        var dropzoneUrl = dropzone.data('url');
        var inputId = dropzone.find(fileIdInputSelector);
        var isImage = inputId.is('[name="image"]');
        var lookupButton = dropzone.find(lookupButtonSelector);
        var message = dropzone.find(messageSelector);
        var clearButton = dropzone.find(filerClearerSelector);
        var fileChoose = dropzone.find(fileChooseSelector);

        checkMinWidth = $.proxy(checkMinWidth, dropzone);

        $(window).on('resize', checkMinWidth);

        new Dropzone(this, {
            url: dropzoneUrl,
            paramName: 'file',
            maxFiles: 1,
            previewTemplate: $(dropzoneTemplateSelector).html(),
            clickable: false,
            addRemoveLinks: false,
            init: function () {
                checkMinWidth();
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
            maxfilesexceeded: function (file) {
                this.removeAllFiles(true);
                this.addFile(file);
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
                }
                $('img', this.element).on('dragstart', function (event) {
                    event.preventDefault();
                });
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
    };

    var dropzones = $(dropzoneSelector);
    if (dropzones.length && Dropzone && !window.filerDropzoneInitialized) {
        window.filerDropzoneInitialized = true;
        dropzones.each(create_dropzone);
        $(document).on('formset:added', function (ev, row) {
            var dropzones = $(row).find(dropzoneSelector);
            dropzones.each(create_dropzone);
        });
    }
});
