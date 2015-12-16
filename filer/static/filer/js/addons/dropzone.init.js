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
        var fileIdInputSelector = $('#id_file');

        if (dropzone.length && Dropzone) {
            Dropzone.autoDiscover = false;
            new Dropzone(dropzoneSelector, {
                url: dropzoneUrl + '?qqfile=userpic-500.jpg',
                paramName: 'file', // The name that will be used to transfer the file
                maxFilesize: 2, // MB
                addRemoveLinks: true,
                maxFiles: 1,
                // previewTemplate: $('.js-dz-template').html(),
                clickable: false,
                maxfilesexceeded: function (file) {
                    this.removeAllFiles();
                    this.addFile(file);
                },
                success: function (isSuccess, responce) {
                    console.log(this);
                    console.log(isSuccess);
                    console.log(responce);

                    if (isSuccess && responce && responce.preview) {
                        $(fileIdInputSelector).val(responce.preview);
                    }
                },
                drop: function () {
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
