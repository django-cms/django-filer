// #DROPZONE#
// This script implements the dropzone settings
'use strict';

/* global Dropzone */
(function ($) {
    $(function () {
        var dropzoneSelector = '.js-dropzone';
        var dataAction = $(dropzoneSelector).data('action');

        if ($(dropzoneSelector).length && Dropzone) {
            Dropzone.autoDiscover = false;
            new Dropzone(dropzoneSelector, {
                url: dataAction,
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
