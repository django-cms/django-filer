from django.contrib import admin
from django.forms.models import modelform_factory
from django.http import JsonResponse
from django.urls import re_path
from django.views.decorators.csrf import csrf_exempt

from .. import settings as filer_settings
from ..models import Clipboard, ClipboardItem, Folder
from ..utils.files import handle_request_files_upload, handle_upload
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
            re_path(r'^operations/paste_clipboard_to_folder/$',
                    self.admin_site.admin_view(views.paste_clipboard_to_folder),
                    name='filer-paste_clipboard_to_folder'),
            re_path(r'^operations/discard_clipboard/$',
                    self.admin_site.admin_view(views.discard_clipboard),
                    name='filer-discard_clipboard'),
            re_path(r'^operations/delete_clipboard/$',
                    self.admin_site.admin_view(views.delete_clipboard),
                    name='filer-delete_clipboard'),
            re_path(r'^operations/upload/(?P<folder_id>[0-9]+)/$',
                    ajax_upload,
                    name='filer-ajax_upload'),
            re_path(r'^operations/upload/no_folder/$',
                    ajax_upload,
                    name='filer-ajax_upload'),
        ] + super().get_urls()

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
    if folder_id:
        try:
            # Get folder
            folder = Folder.objects.get(pk=folder_id)
        except Folder.DoesNotExist:
            return JsonResponse({'error': NO_FOLDER_ERROR})
    else:
        folder = Folder.objects.filter(pk=request.session.get('filer_last_folder_id', 0)).first()

    # check permissions
    if folder and not folder.has_add_children_permission(request):
        return JsonResponse({'error': NO_PERMISSIONS_FOR_FOLDER})

    if len(request.FILES) == 1:
        # dont check if request is ajax or not, just grab the file
        upload, filename, is_raw, mime_type = handle_request_files_upload(request)
    else:
        # else process the request as usual
        upload, filename, is_raw, mime_type = handle_upload(request)
    # TODO: Deprecated/refactor
    # Get clipboad
    # clipboard = Clipboard.objects.get_or_create(user=request.user)[0]

    # find the file type
    for filer_class in filer_settings.FILER_FILE_MODELS:
        FileSubClass = load_model(filer_class)
        # TODO: What if there are more than one that qualify?
        if FileSubClass.matches_file_type(filename, upload, mime_type):
            FileForm = modelform_factory(
                model=FileSubClass,
                fields=('original_filename', 'owner', 'file')
            )
            break
    uploadform = FileForm({'original_filename': filename, 'owner': request.user.pk},
                          {'file': upload})
    uploadform.instance.mime_type = mime_type
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

        thumbnail = None
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
        return JsonResponse({'message': str(form_errors)}, status=422)
