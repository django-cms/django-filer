#-*- coding: utf-8 -*-
from django.forms.models import modelform_factory
from django.contrib import admin
from django.http import HttpResponse
from django.utils import simplejson
from django.views.decorators.csrf import csrf_exempt
from filer import settings as filer_settings
from filer.models import Clipboard, ClipboardItem
from filer.utils.files import handle_upload, UploadException
from filer.utils.loader import load_object


# ModelAdmins
class ClipboardItemInline(admin.TabularInline):
    model = ClipboardItem


class ClipboardAdmin(admin.ModelAdmin):
    model = Clipboard
    inlines = [ClipboardItemInline]
    filter_horizontal = ('files',)
    raw_id_fields = ('user',)
    verbose_name = "DEBUG Clipboard"
    verbose_name_plural = "DEBUG Clipboards"

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urls = super(ClipboardAdmin, self).get_urls()
        from filer import views
        url_patterns = patterns('',
            url(r'^operations/paste_clipboard_to_folder/$',
                self.admin_site.admin_view(views.paste_clipboard_to_folder),
                name='filer-paste_clipboard_to_folder'),
            url(r'^operations/discard_clipboard/$',
                self.admin_site.admin_view(views.discard_clipboard),
                name='filer-discard_clipboard'),
            url(r'^operations/delete_clipboard/$',
                self.admin_site.admin_view(views.delete_clipboard),
                name='filer-delete_clipboard'),
            # upload does it's own permission stuff (because of the stupid
            # flash missing cookie stuff)
            url(r'^operations/upload/$',
                self.ajax_upload,
                name='filer-ajax_upload'),
        )
        url_patterns.extend(urls)
        return url_patterns

    @csrf_exempt
    def ajax_upload(self, request, folder_id=None):
        """
        receives an upload from the uploader. Receives only one file at the time.
        """
        mimetype = "application/json" if request.is_ajax() else "text/html"
        try:
            upload, filename, is_raw = handle_upload(request)

            # Get clipboad
            clipboard = Clipboard.objects.get_or_create(user=request.user)[0]

            # find the file type
            for filer_class in filer_settings.FILER_FILE_MODELS:
                FileSubClass = load_object(filer_class)
                #TODO: What if there are more than one that qualify?
                if FileSubClass.matches_file_type(filename, upload, request):
                    FileForm = modelform_factory(
                        model = FileSubClass,
                        fields = ('original_filename', 'owner', 'file')
                    )
                    break
            uploadform = FileForm({'original_filename': filename,
                                   'owner': request.user.pk},
                                  {'file': upload})
            if uploadform.is_valid():
                file_obj = uploadform.save(commit=False)
                # Enforce the FILER_IS_PUBLIC_DEFAULT
                file_obj.is_public = filer_settings.FILER_IS_PUBLIC_DEFAULT
                file_obj.save()
                clipboard_item = ClipboardItem(
                                    clipboard=clipboard, file=file_obj)
                clipboard_item.save()
                json_response = {
                    'thumbnail': file_obj.icons['32'],
                    'alt_text': '',
                    'label': unicode(file_obj),
                }
                return HttpResponse(simplejson.dumps(json_response),
                                    mimetype=mimetype)
            else:
                form_errors = '; '.join(['%s: %s' % (
                    field,
                    ', '.join(errors)) for field, errors in uploadform.errors.items()
                ])
                raise UploadException("AJAX request not valid: form invalid '%s'" % (form_errors,))
        except UploadException, e:
            return HttpResponse(simplejson.dumps({'error': unicode(e)}),
                                mimetype=mimetype)

    def get_model_perms(self, request):
        """
        It seems this is only used for the list view. NICE :-)
        """
        return {
            'add': False,
            'change': False,
            'delete': False,
        }
