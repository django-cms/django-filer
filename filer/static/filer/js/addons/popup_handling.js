'use strict';
/* global django */

(function ($) {
    window.dismissPopupAndReload = function (win) {
        document.location.reload();
        win.close();
    };
    window.dismissRelatedImageLookupPopup = function (win, chosenId, chosenThumbnailUrl, chosenDescriptionTxt) {
        var name = window.windowname_to_id(win.name);
        var nameElement = document.getElementById(name);
        var id = nameElement.getAttribute('data-id');
        var img = document.getElementById(id + '_thumbnail_img');
        var txt = document.getElementById(id + '_description_txt');
        var clear = document.getElementById(id + '_clear');
        var lookup = document.getElementById(id + '_lookup');
        var dropzone_message = document.getElementById(id + '_dropzone_message');
        var elem = document.getElementById(id);
        var old_id = elem.value;

        elem.value = chosenId;
        img.src = chosenThumbnailUrl;
        txt.innerHTML = chosenDescriptionTxt;
        clear.style.display = 'inline';
        lookup.className += ' hidden';
        dropzone_message.className += ' hidden';

        if (old_id !== chosenId) {
            $(elem).trigger('change');
        }
        win.close();
    };
    window.dismissRelatedFolderLookupPopup = function (win, chosenId, chosenName) {
        var id = window.windowname_to_id(win.name);
        var id_name = id + '_description_txt';
        document.getElementById(id).value = chosenId;
        document.getElementById(id_name).innerHTML = chosenName;
        win.close();
    };
})(django.jQuery);
