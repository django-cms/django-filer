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
        var $container = $lookup.closest(".filerFile");
        var $img = $container.find(".thumbnail_img");
        var $txt = $container.find(".description_txt");
        var $clearer = $container.find(".filerClearer");
        var $dropzoneMessage = $container.siblings(".dz-message");
        var $elem = $container.find(":input");
        var oldId = $elem.value;

        $elem.val(chosenId);
        $elem.closest('.js-filer-dropzone').addClass('js-object-attached');
        $img.attr('src', chosenThumbnailUrl).removeClass('hidden');
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
