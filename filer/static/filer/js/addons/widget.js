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

    $(document).ready(function () {
        $('.filerFile .vForeignKeyRawIdAdminField').attr('type', 'hidden');
        //if this file is included multiple time, we ensure that filer_clear is attached only once.
        $(document).off('click.filer', '.filerFile .filerClearer', filer_clear)
            .on('click.filer', '.filerFile .filerClearer', filer_clear);
    });
})(django.jQuery);


if(window.FormData){
    (function($){
    $(document).ready(function(){

        $('.filerUploader > strong').remove();
        $('.filerUploader > span').show();
        var form = $('FORM .filerUploader').first().closest('form').get(0);
        if(typeof form.filer_uploading === 'undefined'){
            form.filer_uploading = 0 ;
            $(form).submit(function(e){
                if(this.filer_uploading > 0){
                    e.preventDefault();
                    if(this.filer_uploading == 1){
                        msg = this.filerData.msg.wait_sing;
                    }else{
                        msg = this.filerData.msg.wait_plur.replace('%(nb_files)d', this.filer_uploading);
                    }
                    alert(msg);
                }
            });
            $(document).on('click', '.filerUploader .filerChoose', function(e){
                $(this).closest('.filerUploader').find('input[type=file]').trigger('click');
            });
            $(document).on('change', '.filerUploader input[type=file]', function(e){
                var $this = $(this),
                    container = $this.closest('.filerFile'),
                    filerData = container.find('.filerChoose').data('filer'),
                    el_filename = container.find('.filerFilename'),
                    form = container.closest('form').get(0),
                    name = this.value;

                //add translations to the form.
                if(!form.filerData){form.filerData = filerData;}

                if(!name){
                    el_filename.html(filerData.msg.no_file_selected);
                }else{
                    var startIndex = (name.indexOf('\\') >= 0 ? name.lastIndexOf('\\') : name.lastIndexOf('/')),
                        url = filerData.url+'?qqfile='+name;
                    if(filerData.folder_key){
                        url+='&folder_key='+filerData.folder_key;
                    }
                    if(filerData.direct_upload_related_field){
                        url+='&related_field='+filerData.direct_upload_related_field;
                    }
                    if(!form.filer_uploading){
                        container.addClass('fileUploading') ;
                    }
                    name = name.substring(startIndex+1);
                    el_filename.html(name);
                    form.filer_uploading += 1 ;
                    $.ajax({
                         url:url,
                         type: 'POST',
                         data: this.files[0],
                         cache: false,
                         dataType: 'json',
                         contentType: 'application/octet-stream',
                         processData: false,
                         context:container,
                         success: function(data, textStatus, jqXHR){
                            var base_id = '#' + this.find('.vForeignKeyRawIdAdminField').attr('id') ;
                            if(typeof data.error === 'undefined'){
                                $(base_id).attr('value', data.pk);
                                $(base_id+'_thumbnail_img').attr('src', data.thumbnail);
                                $(base_id+'_description_txt').html(data.label);
                                $(base_id+'_clear').show();
                                container.find('.filerFilename').html(filerData.msg.no_file_selected);
                                container.addClass('fileSelected') ;
                                container.find('.filerChoose').html(filerData.msg.choose_replace_file);
                            }else{
                                alert(data.error);
                            }
                            form.filer_uploading -= 1 ;
                         },
                         error: function(jqXHR, textStatus, errorThrown){
                            alert(filerData.msg.error.replace('%(error)s', errorThrown));
                            form.filer_uploading -= 1 ;
                         },
                         complete: function(jqXHR, textStatus){
                            if(!form.filer_uploading){
                                 container.removeClass('fileUploading') ;
                            }
                         }
                    });
                }
            });
        }
    });
    })(window.$ || django.jQuery);
}
