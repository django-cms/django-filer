'use strict';
/* global django */

(function ($) {
    var filer_clear = function () {
        var clearer = $(this);
        var hidden_input = clearer.closest('.filerFile').find('input.vForeignKeyRawIdAdminField');
        var base_id = '#' + hidden_input.attr('id');
        var thumbnail = $(base_id + '_thumbnail_img');
        var description = $(base_id + '_description_txt');
        var addImageButton = $(base_id + '_lookup');
        var dropzoneMessage = $(base_id + '_filer_dropzone_message');
        var hiddenClass = 'hidden';
        var static_prefix = clearer.attr('src').replace('admin/img/icon_deletelink.gif', 'filer/');

        clearer.hide();
        hidden_input.removeAttr('value');
        thumbnail.attr('src', static_prefix + 'icons/nofile_48x48.png');
        thumbnail.parent('a').removeAttr('href');
        addImageButton.removeClass(hiddenClass);
        dropzoneMessage.removeClass(hiddenClass);
        description.empty();
    };

    $(document).ready(function () {
        $('.filerFile .vForeignKeyRawIdAdminField').attr('type', 'hidden');
        //if this file is included multiple time, we ensure that filer_clear is attached only once.
        $(document).off('click.filer', '.filerFile .filerClearer', filer_clear)
            .on('click.filer', '.filerFile .filerClearer', filer_clear);
    });
})(django.jQuery);
