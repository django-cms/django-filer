'use strict';
/* global django */

(function ($) {
    window.dismissPopupAndReload = function (win) {
        document.location.reload();
        win.close();
    };
    window.dismissRelatedImageLookupPopup = function (win, chosenId, chosenThumbnailUrl, chosenDescriptionTxt) {
        var name = window.windowname_to_id(win.name);
        var img_name = name + '_thumbnail_img';
        var txt_name = name + '_description_txt';
        var clear_name = name + '_clear';
        var elem = document.getElementById(name);
        var old_id = elem.value;
        document.getElementById(name).value = chosenId;
        document.getElementById(img_name).src = chosenThumbnailUrl;
        document.getElementById(txt_name).innerHTML = chosenDescriptionTxt;
        document.getElementById(clear_name).style.display = 'inline';
        document.getElementById('lookup_id_file').className += ' hidden';
        document.getElementById('dropzone-message').className += ' hidden';
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
