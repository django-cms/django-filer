// #DROPZONE#
// This script implements the dropzone settings
'use strict';

/* global Dropzone */
(function ($) {
    $(function () {
        var dropzoneSelector = '.js-dropzone';
        var dropzone = $(dropzoneSelector);
        var dropzoneUrl = dropzone.data('url');
        var filerFile = $('.filerFile');

        if (dropzone.length && Dropzone) {
            Dropzone.autoDiscover = false;
            new Dropzone(dropzoneSelector, {
                url: dropzoneUrl,
                paramName: 'file', // The name that will be used to transfer the file
                maxFilesize: 2, // MB
                addRemoveLinks: true,
                maxFiles: 1,
                clickable: false,
                maxfilesexceeded: function (file) {
                    this.removeAllFiles();
                    this.addFile(file);
                },
                drop: function (element) {
                    filerFile.hide();
                    $('.filerClearer').click();
                    dropzone.removeClass('dz-drag-hover');
                },
                init: function () {
                    this.on('removedfile', function () {
                        filerFile.show();
                        this.removeAllFiles();
                    });
                }
            });
        }
    });
})(jQuery);
