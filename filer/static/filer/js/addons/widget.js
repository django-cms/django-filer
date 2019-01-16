'use strict';
/* global django */

// as of Django 2.x we need to check where jQuery is
var djQuery = window.$;

if (django.jQuery) {
    djQuery = django.jQuery;
}

djQuery(function ($) {
    var filer_clear = function () {
        var clearer = $(this);
        var container = clearer.closest('.filerFile');
        var input = container.find(':input');
        var thumbnail = container.find('.thumbnail_img');
        var description = container.find('.description_text');
        var addImageButton = container.find('.lookup');
        var dropzoneMessage = container.siblings('.dz-message');
        var hiddenClass = 'hidden';

        clearer.addClass(hiddenClass);
        input.val('');
        thumbnail.addClass(hiddenClass);
        thumbnail.parent('a').removeAttr('href');
        addImageButton.removeClass('related-lookup-change');
        dropzoneMessage.removeClass(hiddenClass);
        description.empty();
    };

    $('.filerFile .vForeignKeyRawIdAdminField').attr('type', 'hidden');
    //if this file is included multiple time, we ensure that filer_clear is attached only once.
    $(document).off('click.filer', '.filerFile .filerClearer', filer_clear)
               .on('click.filer', '.filerFile .filerClearer', filer_clear);
});
