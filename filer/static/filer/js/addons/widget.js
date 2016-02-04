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

        clearer.hide();
        hidden_input.removeAttr('value');
        thumbnail.addClass(hiddenClass);
        thumbnail.parent('a').removeAttr('href');
        addImageButton.removeClass(hiddenClass);
        dropzoneMessage.removeClass(hiddenClass);
        description.empty();
    };

    $(document).ready(function(){
        $('.filerFile').each(function(){
            $(this).find('.vForeignKeyRawIdAdminField').hide();
            $('#add_' + $(this).data('id')).remove();
        });
        //if this file is included multiple time, we ensure that filer_clear is attached only once.
        $(document).off('click.filer', '.filerFile .filerClearer', filer_clear)
            .on('click.filer', '.filerFile .filerClearer', filer_clear);
    });
})(window.$ || django.jQuery);