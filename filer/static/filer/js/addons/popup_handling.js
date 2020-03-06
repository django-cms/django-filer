'use strict';
/* global django */

// as of Django 2.x we need to check where jQuery is
var djQuery = window.$;

if (django.jQuery) {
    djQuery = django.jQuery;
}

(function ($) {
    window.dismissPopupAndReload = function (win) {
        document.location.reload();
        win.close();
    };
    window.dismissRelatedImageLookupPopup = function (win, chosenId, chosenThumbnailUrl, chosenDescriptionTxt) {
        var id = window.windowname_to_id(win.name);
        var lookup = $('#' + id);
        var container = lookup.closest('.filerFile');
        var image = container.find('.thumbnail_img');
        var descriptionText = container.find('.description_text');
        var clearer = container.find('.filerClearer');
        var dropzoneMessage = container.siblings('.dz-message');
        var element = container.find(':input');
        var oldId = element.value;

        element.val(chosenId);
        element.closest('.js-filer-dropzone').addClass('js-object-attached');
        image.attr('src', chosenThumbnailUrl).removeClass('hidden');
        descriptionText.text(chosenDescriptionTxt);
        clearer.removeClass('hidden');
        lookup.addClass('related-lookup-change');
        dropzoneMessage.addClass('hidden');

        if (oldId !== chosenId) {
            element.trigger('change');
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
})(djQuery);
