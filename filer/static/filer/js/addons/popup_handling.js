'use strict';
/* global django */

(function ($) {
    window.dismissPopupAndReload = function (win) {
        document.location.reload();
        win.close();
    };
    window.dismissRelatedImageLookupPopup = function (win, chosenId, chosenThumbnailUrl, chosenDescriptionTxt) {
        var name = window.windowname_to_id(win.name);
        var nameElement = $('#' + name);
        var id = nameElement.data('id');
        var img = $('#' + id + '_thumbnail_img');
        var txt = $('#' + id + '_description_txt');
        var clear = $('#' + id + '_clear');
        var lookup = $('#' + id + '_lookup');
        var dropzoneMessage = $('#' + id + '_filer_dropzone_message');
        var elem = $('#' + id);
        var oldId = elem.value;

        elem.val(chosenId);
        elem.closest('.js-filer-dropzone').addClass('js-object-attached');
        img.attr('src', chosenThumbnailUrl);
        txt.text(chosenDescriptionTxt);
        clear.removeClass('hidden').removeAttr('style');
        lookup.addClass('hidden');
        dropzoneMessage.addClass('hidden');

        if (oldId !== chosenId) {
            $(elem).trigger('change');
        }
        win.close();
    };
    window.dismissRelatedFolderLookupPopup = function (win, chosenId, chosenName) {
        var id = window.windowname_to_id(win.name);
        var clearButton = $('#id_' + id + '_clear');
        var input = $('#id_' + id);
        var folderName = $('#id_' + id + '_description_txt');
        var addFolderButton = $('#' + id);

        input.val(chosenId);
        folderName.text(chosenName);
        clearButton.removeClass('hidden');
        addFolderButton.addClass('hidden');
        win.close();
    };
})(django.jQuery);
