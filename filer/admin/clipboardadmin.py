import logging

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.forms.models import modelform_factory
from django.http import JsonResponse
from django.urls import path, reverse
from django.utils.translation import gettext_lazy as _

from .. import settings as filer_settings
from ..models import Clipboard, ClipboardItem, Folder
from ..settings import FILER_THUMBNAIL_ICON_SIZE
from ..utils.files import UploadException, handle_request_files_upload, handle_upload
from ..utils.loader import load_model
from ..validation import validate_upload
from . import views


logger = logging.getLogger(__name__)

NO_PERMISSIONS = _("You do not have permission to upload files.")
NO_FOLDER_ERROR = _("Can't find folder to upload. Please refresh and try again")
NO_PERMISSIONS_FOR_FOLDER = _(
    "Can't use this folder, Permission Denied. Please select another folder."
)
UPLOAD_ERROR = _("Upload failed. Please refresh and try again.")


Image = load_model(filer_settings.FILER_IMAGE_MODEL)


def _upload_error(request, message, status):
    """
    Report a failed upload both as a Django message (shown on the next full page
    load) and as a JSON body with a matching HTTP status code, so that the
    uploader - and any proxy in between - can tell a rejected upload from an
    accepted one.
    """
    messages.error(request, message)
    return JsonResponse({'error': str(message)}, status=status)


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
                 self.admin_site.admin_view(ajax_upload),
                 name='filer-ajax_upload'),
            path('operations/upload/no_folder/',
                 self.admin_site.admin_view(ajax_upload),
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


def ajax_upload(request, folder_id=None):
    """
    Receives an upload from the uploader. Receives only one file at a time.
    """

    if not request.user.has_perm("filer.add_file"):
        return _upload_error(request, NO_PERMISSIONS, status=403)

    if folder_id:
        try:
            # Get folder
            folder = Folder.objects.get(pk=folder_id)
        except Folder.DoesNotExist:
            return _upload_error(request, NO_FOLDER_ERROR, status=400)
    else:
        folder = Folder.objects.filter(pk=request.session.get('filer_last_folder_id', 0)).first()

    # check permissions
    if folder and not folder.has_add_children_permission(request):
        return _upload_error(request, NO_PERMISSIONS_FOR_FOLDER, status=403)

    try:
        if len(request.FILES) == 1:
            # don't check if request is ajax or not, just grab the file
            upload, filename, is_raw, mime_type = handle_request_files_upload(request)
        else:
            # else process the request as usual
            upload, filename, is_raw, mime_type = handle_upload(request)
    except UploadException:
        # UploadException describes a malformed request rather than something the
        # uploading user can act on. Log the details instead of echoing them back:
        # exception text may carry internals that should not reach the client.
        logger.warning("Rejected file upload", exc_info=True)
        return _upload_error(request, UPLOAD_ERROR, status=400)
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
            # ValidationError carries a message written for the uploading user
            # (e.g. "HTML upload denied by site security policy"), so it is safe
            # - and useful - to pass on.
            return _upload_error(request, '; '.join(error.messages), status=400)
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
        except Exception:
            # Unexpected server-side failure: log it rather than exposing the
            # exception text, which may reveal internals.
            logger.exception("Failed to build the upload response for file %s", file_obj.pk)
            return _upload_error(request, UPLOAD_ERROR, status=500)
    else:
        form_errors = '; '.join(['{}'.format(
            ', '.join(errors)) for errors in list(uploadform.errors.values())
        ])
        return _upload_error(request, form_errors, status=400)
