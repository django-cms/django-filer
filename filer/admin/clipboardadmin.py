#-*- coding: utf-8 -*-
from django.forms.models import modelform_factory
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.models import User
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt
from filer import settings as filer_settings
from filer.admin.tools import popup_param
from filer.models import Clipboard, ClipboardItem, File, Image, tools
from filer.utils.files import generic_handle_file
from filer.utils.loader import load_object
import os


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
        receives an upload from the flash uploader and fixes the session
        because of the missing cookie. Receives only one file at the time,
        althow it may be a zip file, that will be unpacked.
        """
        try:
            # flashcookie-hack (flash does not submit the cookie, so we send
            # the django sessionid over regular post
            engine = __import__(settings.SESSION_ENGINE, {}, {}, [''])
            session_key = request.POST.get('jsessionid')
            request.session = engine.SessionStore(session_key)
            request.user = User.objects.get(
                                    id=request.session['_auth_user_id'])
            # upload and save the file
            if not request.method == 'POST':
                return HttpResponse("must be POST")
            original_filename = request.POST.get('Filename')
            file = request.FILES.get('Filedata')
            # Get clipboad
            clipboard = Clipboard.objects.get_or_create(user=request.user)[0]
            files = generic_handle_file(file, original_filename)
            file_items = []
            for ifile, iname in files:
                for filer_class in filer_settings.FILER_FILE_MODELS:
                    FileSubClass = load_object(filer_class)
                    #TODO: What if there are more than one that qualify?
                    if FileSubClass.matches_file_type(iname, ifile, request):
                        FileForm = modelform_factory(
                            model = FileSubClass,
                            fields = ('original_filename', 'owner', 'file')
                        )
                        break
                uploadform = FileForm({'original_filename': iname,
                                       'owner': request.user.pk},
                                      {'file': ifile})
                if uploadform.is_valid():
                    try:
                        file = uploadform.save(commit=False)
                        # Enforce the FILER_IS_PUBLIC_DEFAULT
                        file.is_public = filer_settings.FILER_IS_PUBLIC_DEFAULT
                        file.save()
                        file_items.append(file)
                        clipboard_item = ClipboardItem(
                                            clipboard=clipboard, file=file)
                        clipboard_item.save()
                    except Exception, e:
                        pass
                else:
                    pass
        except Exception, e:
            pass
        return render_to_response(
                    'admin/filer/tools/clipboard/clipboard_item_rows.html',
                    {'items': file_items},
                    context_instance=RequestContext(request))

    def get_model_perms(self, request):
        """
        It seems this is only used for the list view. NICE :-)
        """
        return {
            'add': False,
            'change': False,
            'delete': False,
        }
