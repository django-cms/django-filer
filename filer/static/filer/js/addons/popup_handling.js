'use strict';
/* global django */

(function ($) {
    window.dismissPopupAndReload = function (win) {
        document.location.reload();
        win.close();
    };
    window.dismissRelatedImageLookupPopup = function (win, chosenId, chosenThumbnailUrl, chosenDescriptionTxt) {
        var id = window.windowname_to_id(win.name);
        var $lookup = $('#' + id);
        var $container = $lookup.closest('.filerFile');
        var $img = $container.find('.thumbnail_img');
        var $txt = $container.find('.description_txt');
        var $clearer = $container.find('.filerClearer');
        var $dropzoneMessage = $container.siblings('.dz-message');
        var $elem = $container.find(':input');
        var oldId = $elem.value;

        $elem.val(chosenId);
        $img.attr('src', chosenThumbnailUrl);
        $txt.text(chosenDescriptionTxt);
        $clearer.removeClass('hidden');
        $lookup.addClass('hidden');
        $dropzoneMessage.addClass('hidden');

        if (oldId !== chosenId) {
            $elem.trigger('change');
        }
        win.close();
    };
    window.dismissRelatedFolderLookupPopup = function (win, chosenId, chosenName) {
        var id = window.windowname_to_id(win.name);
        $('#' + id).val(chosenId);
        $('#' + id).closest('.js-dropzone').addClass('js-object-attached');
        $('#' + id + '_description_txt').text(chosenName);
        win.close();
    };
})(django.jQuery);
