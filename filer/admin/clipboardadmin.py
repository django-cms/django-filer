from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.forms.models import modelform_factory
from django.http import JsonResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt

from .. import settings as filer_settings
from ..models import Clipboard, ClipboardItem, Folder
from ..settings import FILER_THUMBNAIL_ICON_SIZE
from ..utils.files import handle_request_files_upload, handle_upload
from ..utils.loader import load_model
from ..validation import validate_upload
from . import views


NO_PERMISSIONS = _("You do not have permission to upload files.")
NO_FOLDER_ERROR = _("Can't find folder to upload. Please refresh and try again")
NO_PERMISSIONS_FOR_FOLDER = _(
    "Can't use this folder, Permission Denied. Please select another folder."
)


Image = load_model(filer_settings.FILER_IMAGE_MODEL)


# ModelAdmins
class ClipboardItemInline(admin.TabularInline):
    model = ClipboardItem


class ClipboardAdmin(admin.ModelAdmin):
    model = Clipboard
    inlines = [ClipboardItemInline]
    raw_id_fields = ('user',)
    verbose_name = "DEBUG Clipboard"
    verbose_name_plural = "DEBUG Clipboards"

    def get_urls(self):
        return [
            path('operations/paste_clipboard_to_folder/',
                 self.admin_site.admin_view(views.paste_clipboard_to_folder),
                 name='filer-paste_clipboard_to_folder'),
            path('operations/discard_clipboard/',
                 self.admin_site.admin_view(views.discard_clipboard),
                 name='filer-discard_clipboard'),
            path('operations/delete_clipboard/',
                 self.admin_site.admin_view(views.delete_clipboard),
                 name='filer-delete_clipboard'),
            path('operations/upload/<int:folder_id>/',
                 ajax_upload,
                 name='filer-ajax_upload'),
            path('operations/upload/no_folder/',
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

    if not request.user.has_perm("filer.add_file"):
        messages.error(request, NO_PERMISSIONS)
        return JsonResponse({'error': NO_PERMISSIONS})

    if folder_id:
        try:
            # Get folder
            folder = Folder.objects.get(pk=folder_id)
        except Folder.DoesNotExist:
            messages.error(request, NO_FOLDER_ERROR)
            return JsonResponse({'error': NO_FOLDER_ERROR})
    else:
        folder = Folder.objects.filter(pk=request.session.get('filer_last_folder_id', 0)).first()

    # check permissions
    if folder and not folder.has_add_children_permission(request):
        messages.error(request, NO_PERMISSIONS_FOR_FOLDER)
        return JsonResponse({'error': NO_PERMISSIONS_FOR_FOLDER})

    if len(request.FILES) == 1:
        # don't check if request is ajax or not, just grab the file
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
    uploadform.request = request
    uploadform.instance.mime_type = mime_type
    if uploadform.is_valid():
        try:
            validate_upload(filename, upload, request.user, mime_type)
            file_obj = uploadform.save(commit=False)
            # Enforce the FILER_IS_PUBLIC_DEFAULT
            file_obj.is_public = filer_settings.FILER_IS_PUBLIC_DEFAULT
        except ValidationError as error:
            messages.error(request, str(error))
            return JsonResponse({'error': str(error)})
        file_obj.folder = folder
        file_obj.save()
        # TODO: Deprecated/refactor
        # clipboard_item = ClipboardItem(
        #     clipboard=clipboard, file=file_obj)
        # clipboard_item.save()

        try:
            thumbnail = None
            data = {
                'thumbnail': thumbnail,
                'alt_text': '',
                'label': str(file_obj),
                'file_id': file_obj.pk,
            }
            # prepare preview thumbnail
            if isinstance(file_obj, Image):
                data['thumbnail_180'] = reverse(
                    f"admin:filer_{file_obj._meta.model_name}_fileicon",
                    args=(file_obj.pk, FILER_THUMBNAIL_ICON_SIZE),
                )
                data['original_image'] = file_obj.url
            return JsonResponse(data)
        except Exception as error:
            messages.error(request, str(error))
            return JsonResponse({"error": str(error)})
    else:
        for key, error_list in uploadform.errors.items():
            for error in error_list:
                messages.error(request, error)

        form_errors = '; '.join(['{}'.format(
            ', '.join(errors)) for errors in list(uploadform.errors.values())
        ])
        return JsonResponse({'error': str(form_errors)}, status=200)
