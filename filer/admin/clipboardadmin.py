# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.conf.urls import url
from django.contrib import admin
from django.forms.models import modelform_factory
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .. import settings as filer_settings
from ..models import Clipboard, ClipboardItem, Folder
from ..utils.files import (
    UploadException, handle_request_files_upload, handle_upload,
)
from ..utils.loader import load_model
from . import views


NO_FOLDER_ERROR = "Can't find folder to upload. Please refresh and try again"
NO_PERMISSIONS_FOR_FOLDER = (
    "Can't use this folder, Permission Denied. Please select another folder."
)


Image = load_model(filer_settings.FILER_IMAGE_MODEL)


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
        return [
            url(r'^operations/paste_clipboard_to_folder/$',
                self.admin_site.admin_view(views.paste_clipboard_to_folder),
                name='filer-paste_clipboard_to_folder'),
            url(r'^operations/discard_clipboard/$',
                self.admin_site.admin_view(views.discard_clipboard),
                name='filer-discard_clipboard'),
            url(r'^operations/delete_clipboard/$',
                self.admin_site.admin_view(views.delete_clipboard),
                name='filer-delete_clipboard'),
            url(r'^operations/upload/(?P<folder_id>[0-9]+)/$',
                ajax_upload,
                name='filer-ajax_upload'),
            url(r'^operations/upload/no_folder/$',
                ajax_upload,
                name='filer-ajax_upload'),
        ] + super(ClipboardAdmin, self).get_urls()

    def get_model_perms(self, *args, **kwargs):
        """
        It seems this is only used for the list view. NICE :-)
        """
        return {
            'add': False,
            'change': False,
            'delete': False,
        }


@csrf_exempt
def ajax_upload(request, folder_id=None):
    """
    Receives an upload from the uploader. Receives only one file at a time.
    """
    folder = None
    if folder_id:
        try:
            # Get folder
            folder = Folder.objects.get(pk=folder_id)
        except Folder.DoesNotExist:
            return JsonResponse({'error': NO_FOLDER_ERROR})

    # check permissions
    if folder and not folder.has_add_children_permission(request):
        return JsonResponse({'error': NO_PERMISSIONS_FOR_FOLDER})
    try:
        if len(request.FILES) == 1:
            # dont check if request is ajax or not, just grab the file
            upload, filename, is_raw = handle_request_files_upload(request)
        else:
            # else process the request as usual
            upload, filename, is_raw = handle_upload(request)
        # TODO: Deprecated/refactor
        # Get clipboad
        # clipboard = Clipboard.objects.get_or_create(user=request.user)[0]

        # find the file type
        for filer_class in filer_settings.FILER_FILE_MODELS:
            FileSubClass = load_model(filer_class)
            # TODO: What if there are more than one that qualify?
            if FileSubClass.matches_file_type(filename, upload, request):
                FileForm = modelform_factory(
                    model=FileSubClass,
                    fields=('original_filename', 'owner', 'file')
                )
                break
        uploadform = FileForm({'original_filename': filename,
                               'owner': request.user.pk},
                              {'file': upload})
        if uploadform.is_valid():
            file_obj = uploadform.save(commit=False)
            # Enforce the FILER_IS_PUBLIC_DEFAULT
            file_obj.is_public = filer_settings.FILER_IS_PUBLIC_DEFAULT
            file_obj.folder = folder
            file_obj.save()
            # TODO: Deprecated/refactor
            # clipboard_item = ClipboardItem(
            #     clipboard=clipboard, file=file_obj)
            # clipboard_item.save()

            # Try to generate thumbnails.
            if not file_obj.icons:
                # There is no point to continue, as we can't generate
                # thumbnails for this file. Usual reasons: bad format or
                # filename.
                file_obj.delete()
                # This would be logged in BaseImage._generate_thumbnails()
                # if FILER_ENABLE_LOGGING is on.
                return JsonResponse(
                    {'error': 'failed to generate icons for file'},
                    status=500,
                )
            thumbnail = None
            # Backwards compatibility: try to get specific icon size (32px)
            # first. Then try medium icon size (they are already sorted),
            # fallback to the first (smallest) configured icon.
            for size in (['32']
                        + filer_settings.FILER_ADMIN_ICON_SIZES[1::-1]):
                try:
                    thumbnail = file_obj.icons[size]
                    break
                except KeyError:
                    continue

            data = {
                'thumbnail': thumbnail,
                'alt_text': '',
                'label': str(file_obj),
                'file_id': file_obj.pk,
            }
            # prepare preview thumbnail
            if type(file_obj) == Image:
                thumbnail_180_options = {
                    'size': (180, 180),
                    'crop': True,
                    'upscale': True,
                }
                thumbnail_180 = file_obj.file.get_thumbnail(
                    thumbnail_180_options)
                data['thumbnail_180'] = thumbnail_180.url
                data['original_image'] = file_obj.url
            return JsonResponse(data)
        else:
            form_errors = '; '.join(['%s: %s' % (
                field,
                ', '.join(errors)) for field, errors in list(
                    uploadform.errors.items())
            ])
            raise UploadException(
                "AJAX request not valid: form invalid '%s'" % (
                    form_errors,))
    except UploadException as e:
        return JsonResponse({'error': str(e)}, status=500)
