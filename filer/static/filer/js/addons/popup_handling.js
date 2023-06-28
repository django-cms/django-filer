'use strict';
/* global django */

// as of Django 2.x we need to check where jQuery is
var djQuery = window.$;

if (django.jQuery) {
    djQuery = django.jQuery;
}

(function ($) {
    function windowname_to_id(text) {
        text = text.replace(/__dot__/g, '.');
        text = text.replace(/__dash__/g, '-');
        return text.split('__')[0];
    }

    window.dismissPopupAndReload = function (win) {
        document.location.reload();
        win.close();
    };
    window.dismissRelatedImageLookupPopup = function (
        win,
        chosenId,
        chosenThumbnailUrl,
        chosenDescriptionTxt,
        chosenAdminChangeUrl
    ) {
        var id = windowname_to_id(win.name);
        var lookup = $('#' + id);
        var container = lookup.closest('.filerFile');
        var edit = container.find('.edit');
        var image = container.find('.thumbnail_img');
        var descriptionText = container.find('.description_text');
        var clearer = container.find('.filerClearer');
        var dropzoneMessage = container.siblings('.dz-message');
        var element = container.find(':input');
        var oldId = element.value;

        element.val(chosenId);
        element.closest('.js-filer-dropzone').addClass('js-object-attached');
        if (chosenThumbnailUrl) {
            image.attr('src', chosenThumbnailUrl).removeClass('hidden');
            image.removeAttr('srcset'); // would be nicer, but much more complicate to also replace 'srcset'
        }
        descriptionText.text(chosenDescriptionTxt);
        clearer.removeClass('hidden');
        lookup.addClass('related-lookup-change');
        edit.addClass('related-lookup-change');
        if (chosenAdminChangeUrl) {
            edit.attr('href', chosenAdminChangeUrl + '?_edit_from_widget=1');
        }
        dropzoneMessage.addClass('hidden');

        if (oldId !== chosenId) {
            element.trigger('change');
        }
        win.close();
    };
    window.dismissRelatedFolderLookupPopup = function (win, chosenId, chosenName) {
        var id = windowname_to_id(win.name);
        var lookup = $('#' + id);
        var container = lookup.closest('.filerFile');
        var image = container.find('.thumbnail_img');
        var clearButton = $('#id_' + id + '_clear');
        var input = $('#id_' + id);
        var folderName = container.find('.description_text');
        var addFolderButton = $('#' + id);

        input.val(chosenId);

        image.removeClass('hidden');
        folderName.text(chosenName);
        clearButton.removeClass('hidden');
        addFolderButton.addClass('hidden');
        win.close();
    };
})(djQuery);
