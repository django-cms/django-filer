(function($) {
    var filer_clear = function(e){
        var clearer = $(this),
            hidden_input = clearer.closest('.filerFile').find('input.vForeignKeyRawIdAdminField'),
            base_id = '#'+hidden_input.attr('id'),
            thumbnail = $(base_id+'_thumbnail_img'),
            description = $(base_id+'_description_txt'),
            static_prefix = clearer.attr('src').replace('admin/img/icon_deletelink.gif', 'filer/');
        clearer.hide();
        hidden_input.removeAttr("value");
        thumbnail.attr("src", static_prefix+"icons/nofile_48x48.png");
        description.html("");
    }

    $(document).ready(function(){
        $('.filerFile .vForeignKeyRawIdAdminField').attr('type', 'hidden');
        //if this file is included multiple time, we ensure that filer_clear is attached only once.
        $(document).off('click.filer', '.filerFile .filerClearer', filer_clear).on('click.filer', '.filerFile .filerClearer', filer_clear);
    });
})(django.jQuery);
