// #DROPZONE#
// This script implements the dropzone settings
'use strict';

/* global Dropzone */
(function ($) {
    $(function () {
        var dropzoneSelector = '.js-dropzone';
        var dropzone = $(dropzoneSelector);
        var dropzoneUrl = dropzone.data('url');

        if (dropzone.length && Dropzone) {
            Dropzone.autoDiscover = false;
            new Dropzone('.js-dropzone', {
                url: dropzoneUrl,
                paramName: 'file', // The name that will be used to transfer the file
                maxFilesize: 2, // MB
                addRemoveLinks: true,
                maxFiles: 1,
                maxfilesexceeded: function (file) {
                    this.removeAllFiles();
                    this.addFile(file);
                }
            });
        }
    });
})(jQuery);
