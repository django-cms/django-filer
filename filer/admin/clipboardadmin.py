import os
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseBadRequest
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.contrib import admin
from django import forms
from django.contrib.admin.models import User
from django.conf import settings
from filer.models import Clipboard, ClipboardItem, File, Image
from filer.utils.files import generic_handle_file
from filer.models import tools
from filer import settings as filer_settings
from filer.admin.tools import popup_param
from filer.admin.upload import handle_upload, UploadException
from django.views.decorators.csrf import csrf_exempt

# forms... sucks, types should be automatic
class UploadFileForm(forms.ModelForm):
    class Meta:
        model = File
class UploadImageFileForm(forms.ModelForm):
    class Meta:
        model = Image


# ModelAdmins
class ClipboardItemInline(admin.TabularInline):
    model = ClipboardItem
class ClipboardAdmin(admin.ModelAdmin):
    model = Clipboard
    inlines = [ ClipboardItemInline, ]
    filter_horizontal = ('files',)
    raw_id_fields = ('user',)
    verbose_name = "DEBUG Clipboard"
    verbose_name_plural = "DEBUG Clipboards"
    
    def get_urls(self):
        from django.conf.urls.defaults import patterns, url
        urls = super(ClipboardAdmin, self).get_urls()
        from filer import views
        url_patterns = patterns('',
            #url(r'^([0-9]+)/move-page/$', self.admin_site.admin_view(self.move_entity), name='%s_%s' % (info, 'move_page') ),
            url(r'^operations/paste_clipboard_to_folder/$',
                self.admin_site.admin_view(views.paste_clipboard_to_folder),
                name='filer-paste_clipboard_to_folder'),
            url(r'^operations/discard_clipboard/$',
                self.admin_site.admin_view(views.discard_clipboard),
                name='filer-discard_clipboard'),
            url(r'^operations/delete_clipboard/$',
                self.admin_site.admin_view(views.delete_clipboard),
                name='filer-delete_clipboard'),
            url(r'^operations/move_file_to_clipboard/$',
                self.admin_site.admin_view(self.move_file_to_clipboard),
                name='filer-move_file_to_clipboard'),
            # upload does it's own permission stuff (because of the stupid flash missing cookie stuff)
            url(r'^operations/upload/$',
                self.ajax_upload,
                name='filer-ajax_upload'),
        )
        url_patterns.extend(urls)
        return url_patterns
    #def has_add_permission(self, request):
    #    return False
    #def has_change_permission(self, request, obj=None):
    #    return False
    #def has_delete_permission(self, request, obj=None):
    #    return False
    @csrf_exempt
    def ajax_upload(self, request, folder_id=None):
        """
        receives an upload from the flash uploader and fixes the session
        because of the missing cookie. Receives only one file at the time, 
        althow it may be a zip file, that will be unpacked.
        """
        try:
            upload, filename, is_raw = handle_upload(request)

            # Get clipboad
            clipboard, was_clipboard_created = Clipboard.objects.get_or_create(user=request.user)
            files = generic_handle_file(upload, filename)
            file_items = []
            for ifile, iname in files:
                try:
                    iext = os.path.splitext(iname)[1].lower()
                except:
                    iext = ''
                if iext in ['.jpg', '.jpeg', '.png', '.gif']:
                    uploadform = UploadImageFileForm({'original_filename':iname,
                                                      'owner': request.user.pk},
                                                    {'file':ifile})
                else:
                    uploadform = UploadFileForm({'original_filename':iname,
                                                 'owner': request.user.pk},
                                                {'file':ifile})
                if uploadform.is_valid():
                    try:
                        file = uploadform.save(commit=False)
                        # Enforce the FILER_IS_PUBLIC_DEFAULT
                        file.is_public = filer_settings.FILER_IS_PUBLIC_DEFAULT
                        file.save()
                        file_items.append(file)
                        clipboard_item = ClipboardItem(clipboard=clipboard, file=file)
                        clipboard_item.save()
                    except Exception, e:
                        #print e
                        pass
                else:
                    pass#print uploadform.errors
        except Exception, e:
            #print e
            pass
        return render_to_response('admin/filer/tools/clipboard/upload_response.json',
                                  {'items': file_items },
                                  context_instance=RequestContext(request))
    def move_file_to_clipboard(self, request):
        #print "move file"
        if request.method == 'POST':
            file_id = request.POST.get("file_id", None)
            clipboard = tools.get_user_clipboard(request.user)
            if file_id:
                file = File.objects.get(id=file_id)
                if file.has_edit_permission(request):
                    tools.move_file_to_clipboard([file], clipboard)
                else:
                    raise PermissionDenied
        return HttpResponseRedirect( '%s%s' % (request.POST.get('redirect_to', ''), popup_param(request) ) )
    def get_model_perms(self, request):
        """
        It seems this is only used for the list view. NICE :-)
        """
        return {
            'add': False,
            'change': False,
            'delete': False,
        }

