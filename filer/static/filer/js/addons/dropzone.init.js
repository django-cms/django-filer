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
        var lookupSelector = '.js-related-lookup';
        var progressSelector = '.js-dropzone-progress';
        var previewImageWrapperSelector = '.js-img-wrapper';
        var filerClearerSelector = '.filerClearer';
        var dropzone = $(dropzoneSelector);
        var dropzoneUrl = dropzone.data('url');
        var fileSelector = $('.js-file-selector');
        var fileIdInputSelector = $('#id_file');
        var hiddenClass = 'hidden';

        if (dropzone.length && Dropzone) {
            Dropzone.autoDiscover = false;
            new Dropzone(dropzoneSelector, {
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
                    $(filerClearerSelector).click();
                    fileSelector.hide();
                    $(lookupSelector).addClass(hiddenClass);
                    $(messageSelector).addClass(hiddenClass);
                    dropzone.removeClass('dz-drag-hover');
                },
                success: function (file, responce) {
                    $(progressSelector).addClass(hiddenClass);
                    if (file && file.status === 'success' && responce) {
                        if (responce.file_id) {
                            $(fileIdInputSelector).val(responce.file_id);
                        }
                        if (responce.thumbnail_180) {
                            $(previewImageSelector).css({'background-image': 'url(' + responce.thumbnail_180 + ')'});
                            $(previewImageWrapperSelector).removeClass(hiddenClass);
                        }
                    }
                },
                reset: function () {
                    $(previewImageWrapperSelector).addClass(hiddenClass);
                    $(fileIdInputSelector).val('');
                    $(lookupSelector).removeClass(hiddenClass);
                    $(messageSelector).removeClass(hiddenClass);
                }
            });
        }
    });
})(jQuery);
