// #DROPZONE#
// This script implements the dropzone settings
'use strict';

/* global Dropzone */
(function ($) {
    $(function () {
        var dropzoneTemplateSelector = '.js-dropzone-template';
        var previewImageSelector = '.js-img-preview';
        var dropzoneSelector = '.js-dropzone';
        var messageSelector = '.js-dropzone-message';
        var lookupButtonSelector = '.js-related-lookup';
        var progressSelector = '.js-dropzone-progress';
        var previewImageWrapperSelector = '.js-img-wrapper';
        var filerClearerSelector = '.filerClearer';
        var dropzones = $(dropzoneSelector);
        var fileSelector = $('.js-file-selector');
        var fileIdInputSelector = '.vForeignKeyRawIdAdminField';
        var hiddenClass = 'hidden';

        if (dropzones.length && Dropzone && !window.initEnabled) {
            window.initEnabled = true;
            Dropzone.autoDiscover = false;
            dropzones.each(function () {
                var dropzone = $(this);
                var dropzoneUrl = dropzone.data('url');
                var inputId = dropzone.find(fileIdInputSelector);
                var isImage = inputId.is('[name="image"]');
                var lookupButton = dropzone.find(lookupButtonSelector);
                var message = dropzone.find(messageSelector);
                var clearButton = dropzone.find(filerClearerSelector);

                new Dropzone(this, {
                    url: dropzoneUrl,
                    paramName: 'file',
                    maxFiles: 1,
                    previewTemplate: $(dropzoneTemplateSelector).html(),
                    clickable: false,
                    addRemoveLinks: false,
                    init: function () {
                        this.on('removedfile', function () {
                            fileSelector.show();
                            this.removeAllFiles();
                        });
                    },
                    maxfilesexceeded: function (file) {
                        this.removeAllFiles();
                        this.addFile(file);
                    },
                    drop: function () {
                        clearButton.click();
                        fileSelector.hide();
                        lookupButton.addClass(hiddenClass);
                        message.addClass(hiddenClass);
                        dropzone.removeClass('dz-drag-hover');
                    },
                    success: function (file, response) {
                        $(progressSelector).addClass(hiddenClass);
                        if (file && file.status === 'success' && response) {
                            if (response.file_id) {
                                inputId.val(response.file_id);
                            }
                            if (response.thumbnail_180) {
                                if (isImage) {
                                    $(previewImageSelector).css({'background-image': 'url(' + response.thumbnail_180 + ')'});
                                    $(previewImageWrapperSelector).removeClass(hiddenClass);
                                }
                            }
                        }
                    },
                    reset: function () {
                        if (isImage) {
                            $(previewImageWrapperSelector).addClass(hiddenClass);
                            $(previewImageSelector).css({'background-image': 'none'});
                        }
                        inputId.val('');
                        lookupButton.removeClass(hiddenClass);
                        message.removeClass(hiddenClass);
                    }
                });
            });
        }
    });
})(jQuery);
