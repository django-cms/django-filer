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
        var dropzoneMessage = $('#' + id + '_dropzone_message');
        var elem = $('#' + id);
        var oldId = elem.value;

        elem.val(chosenId);
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
        $('#' + id).val(chosenId);
        $('#' + id + '_description_txt').text(chosenName);
        win.close();
    };
})(django.jQuery);
