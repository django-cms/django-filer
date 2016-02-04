# -*- coding: utf-8 -*-

import json
from django.forms.models import modelform_factory
from django.contrib import admin
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from filer import settings as filer_settings
from filer.models import Folder, Clipboard, ClipboardItem, Image
from filer.utils.compatibility import DJANGO_1_4, get_model
from filer.utils.files import (
    handle_upload, handle_request_files_upload, UploadException,
)
from filer.utils.loader import load_object
from filer.validators import FileMimetypeValidator


NO_FOLDER_ERROR = "Can't find folder to upload. Please refresh and try again"
NO_PERMISSIONS_FOR_FOLDER = (
    "Can't use this folder, Permission Denied. Please select another folder."
)


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
            url(r'^operations/upload/(?P<folder_id>[0-9]+)/$',
                ajax_upload,
                name='filer-ajax_upload'),
            url((r'^operations/upload/'
                 r'(?P<folder_key>\w*)/'
                 r'(?P<related_field>\w+.\w+.\w+)/'
                 r'$'),
                ajax_upload,
                name='filer-ajax_upload'),
            url((r'^operations/upload/(?P<folder_key>\w*)/$'),
                ajax_upload,
                name='filer-ajax_upload'),
            url((r'^operations/upload/no_folder/$'),
                ajax_upload,
                name='filer-ajax_upload'),
        )
        url_patterns.extend(urls)
        return url_patterns

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
def ajax_upload(request, folder_id=None, folder_key=None, related_field=None):
    """
    Receives an upload from the uploader. Receives only one file at a time.
    """
    mimetype = "application/json" if request.is_ajax() else "text/html"
    content_type_key = 'mimetype' if DJANGO_1_4 else 'content_type'
    response_params = {content_type_key: mimetype}
    mimetypes = []
    try:
        if related_field:
            related_field = related_field.split('.')
            if len(related_field) != 3:
                raise UploadException("Related field is not valid.")
            try:
                model = get_model(related_field[0], related_field[1])
                field = model._meta.get_field_by_name(related_field[2])[0]
            except:
                raise UploadException("Related field is not valid.")
            for validator in field.validators:
                if isinstance(validator, FileMimetypeValidator):
                    mimetypes += validator.mimetypes
        folder = None
        if folder_id:
            try:
                # Get folder
                folder = Folder.objects.get(pk=folder_id)
            except Folder.DoesNotExist:
                return HttpResponse(json.dumps({'error': NO_FOLDER_ERROR}),
                                    **response_params)
        elif folder_key and folder_key != 'no_folder':
            from filer.utils.folders import get_default_folder_getter
            folder = get_default_folder_getter().get(folder_key, request)

        # check permissions
        if folder and not folder.has_add_children_permission(request):
            raise UploadException(NO_PERMISSIONS_FOR_FOLDER)
        if len(request.FILES) == 1:
            # dont check if request is ajax or not, just grab the file
            upload, filename, is_raw = handle_request_files_upload(request, mimetypes)
        else:
            # else process the request as usual
            upload, filename, is_raw = handle_upload(request, mimetypes)
        # TODO: Deprecated/refactor
        # Get clipboad
        # clipboard = Clipboard.objects.get_or_create(user=request.user)[0]

        # find the file type
        for filer_class in filer_settings.FILER_FILE_MODELS:
            FileSubClass = load_object(filer_class)
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
                return HttpResponse(
                    json.dumps(
                        {'error': 'failed to generate icons for file'}),
                    status=500,
                    **response_params)

            thumbnail = None
            # Backwards compatibility: try to get specific icon size (32px)
            # first. Then try medium icon size (they are already sorted),
            # fallback to the first (smallest) configured icon.
            for size in (['32'] +
                         filer_settings.FILER_ADMIN_ICON_SIZES[1::-1]):
                try:
                    thumbnail = file_obj.icons[size]
                    break
                except KeyError:
                    continue

            json_response = {
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
                json_response['thumbnail_180'] = thumbnail_180.url
                json_response['original_image'] = file_obj.url
            return HttpResponse(json.dumps(json_response),
                                **response_params)
        else:
            form_errors = '; '.join(['%s: %s' % (
                fieldname,
                ', '.join(errors)) for fieldname, errors in list(
                    uploadform.errors.items())
            ])
            raise UploadException(
                "AJAX request not valid: form invalid '%s'" % (
                    form_errors,))
    except UploadException as e:
        return HttpResponse(json.dumps({'error': str(e)}),
                            # status=500, we know what's going on and must display it to the user
                            **response_params)
