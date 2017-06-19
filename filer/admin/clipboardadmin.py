#-*- coding: utf-8 -*-
from django.forms.models import modelform_factory
from django.core.exceptions import PermissionDenied
from django.contrib import admin
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from filer import settings as filer_settings
from filer.models import Clipboard, ClipboardItem, Folder, tools
from filer.utils.files import (
    handle_upload, UploadException, matching_file_subtypes
)
from filer.views import (
    popup_param, selectfolder_param, current_site_param,
    file_type_param
)
from filer.admin.tools import is_valid_destination
import imghdr
import os
import json

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
        from django.conf.urls import patterns, url
        urls = super(ClipboardAdmin, self).get_urls()
        url_patterns = patterns('',
            url(r'^operations/paste_clipboard_to_folder/$',
                self.admin_site.admin_view(self.paste_clipboard_to_folder),
                name='filer-paste_clipboard_to_folder'),
            url(r'^operations/discard_clipboard/$',
                self.admin_site.admin_view(self.discard_clipboard),
                name='filer-discard_clipboard'),
            url(r'^operations/delete_clipboard/$',
                self.admin_site.admin_view(self.delete_clipboard),
                name='filer-delete_clipboard'),
            # upload does it's own permission stuff (because of the stupid
            # flash missing cookie stuff)
            url(r'^operations/upload/$',
                self.ajax_upload,
                name='filer-ajax_upload'),
        )
        url_patterns.extend(urls)
        return url_patterns

    def get_clipboard(self, request):
        return Clipboard.objects.get(id=request.POST.get('clipboard_id'))

    def make_clipboard_redirect(self, request):
        return HttpResponseRedirect('%s%s%s%s%s' % (
            request.POST.get('redirect_to', ''),
            popup_param(request),
            selectfolder_param(request),
            current_site_param(request),
            file_type_param(request)))

    def paste_clipboard_to_folder(self, request):
        if request.method == 'POST':
            folder_id = request.POST.get('folder_id')
            if not folder_id:
                raise PermissionDenied
            folder = Folder.objects.get(id=folder_id)
            if not is_valid_destination(request, folder):
                raise PermissionDenied

            clipboard = self.get_clipboard(request)
            files_moved = tools.move_files_from_clipboard_to_folder(
                request, clipboard, folder)
            tools.discard_clipboard_files(clipboard, files_moved)
        return self.make_clipboard_redirect(request)

    def discard_clipboard(self, request):
        if request.method == 'POST':
            clipboard = self.get_clipboard(request)
            tools.discard_clipboard(clipboard)
        return self.make_clipboard_redirect(request)

    def delete_clipboard(self, request):
        if request.method == 'POST':
            tools.delete_clipboard(self.get_clipboard(request))
        return self.make_clipboard_redirect(request)

    def clone_files_from_clipboard_to_folder(self, request):
        if request.method == 'POST':
            folder_id = request.POST.get('folder_id')
            if not folder_id:
                raise PermissionDenied
            folder = Folder.objects.get(id=folder_id)
            if not is_valid_destination(request, folder):
                raise PermissionDenied
            tools.clone_files_from_clipboard_to_folder(
                self.get_clipboard(request), folder)
        return self.make_clipboard_redirect(request)

    @csrf_exempt
    def ajax_upload(self, request, folder_id=None):
        """
        receives an upload from the uploader. Receives only one file at the time.
        """
        mimetype = "application/json" if request.is_ajax() else "text/html"
        upload, file_obj = None ,None
        try:
            upload, filename, is_raw = handle_upload(request)

            extension = os.path.splitext(filename)[1]
            if not extension:
                # try to guess if it's an image and append extension
                # imghdr will detect file is a '.jpeg', '.png' or '.gif' image
                guessed_extension = imghdr.what(upload)
                if guessed_extension:
                    filename = '%s.%s' % (filename, guessed_extension)

            # Get clipboad
            clipboard = Clipboard.objects.get_or_create(user=request.user)[0]
            if any(f for f in clipboard.files.all() if f.original_filename == filename):
                raise UploadException(
                    _(u"A file named %s already exists in the clipboard") % filename)
            matched_file_types = matching_file_subtypes(filename, upload, request)
            FileForm = modelform_factory(
                model=matched_file_types[0],
                fields=('original_filename', 'owner', 'file')
            )
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
                return HttpResponse(json.dumps(json_response),
                                    content_type=mimetype)
            else:
                form_errors = '; '.join(['%s: %s' % (
                    field,
                    ', '.join(errors)) for field, errors in uploadform.errors.items()
                ])
                raise UploadException("AJAX request not valid: form invalid '%s'" % (form_errors,))
        except UploadException, e:
            return HttpResponse(json.dumps({'error': unicode(e)}),
                                content_type=mimetype)
        finally:
            if upload:
                upload.close()
            if file_obj and file_obj.file:
                file_obj.file.close()

    def get_model_perms(self, request):
        """
        It seems this is only used for the list view. NICE :-)
        """
        return {
            'add': False,
            'change': False,
            'delete': False,
        }
