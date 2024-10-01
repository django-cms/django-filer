import hashlib
import mimetypes
from pathlib import Path
import zipfile

from django.contrib import admin
from django.core.files.storage import default_storage
from django.http.response import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.urls import path
from django.utils.translation import gettext

from finder.admin.file import FileAdmin
from finder.contrib.archive.models import ArchiveModel
from finder.models.file import FileModel
from finder.models.folder import FolderModel


class ArchiveAdmin(FileAdmin):
    """
    Admin class for archived file types like ZIP, tar and tar.gz.
    """
    def get_editor_urls(self):
        urls = [
            path(
                '<uuid:file_id>/unarchive',
                self.admin_site.admin_view(self.unarchive_file),
            ),
        ]
        urls.extend(super().get_editor_urls())
        return urls

    def get_menu_extension_urls(self):
        urls = [
            path(
                '<uuid:folder_id>/archive',
                self.admin_site.admin_view(self.archive_selected),
            ),
        ]
        urls.extend(super().get_menu_extension_urls())
        return urls

    # def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
    #     context.update(
    #         unarchive_url=reverse('admin:finder_archive_unarchive_file', args=[obj.pk]) if obj else '',
    #     )
    #     return super().render_change_form(request, context, add, change, form_url, obj)

    def archive_selected(self, request, folder_id):
        if request.method != 'POST':
            return HttpResponseBadRequest(f"Method {request.method} not allowed. Only POST requests are allowed.")
        if not (folder_obj := self.get_object(request, folder_id)):
            return HttpResponseNotFound(f"Folder {folder_id} not found.")
        return HttpResponse(f"Archived successfully.")

    def unarchive_file(self, request, file_id):
        if request.method != 'POST':
            return HttpResponseBadRequest(f"Method {request.method} not allowed. Only POST requests are allowed.")
        if not (zip_file_obj := self.get_object(request, file_id)):
            return HttpResponseNotFound(f"File {file_id} not found.")
        if FolderModel.objects.filter(
            name=zip_file_obj.name,
            parent=zip_file_obj.folder,
            site=self.admin_site.name
        ).exists():
            msg = gettext("Can not extract archive. A folder named “{name}” already exists.")
            return HttpResponseBadRequest(msg.format(name=zip_file_obj.name), status=409)
        try:
            folder_obj = FolderModel.objects.create(
                name=zip_file_obj.name,
                parent=zip_file_obj.folder,
                site=self.admin_site.name,
                owner=request.user,
            )
            zip_file_path = default_storage.path(zip_file_obj.file_path)
            with zipfile.ZipFile(zip_file_path) as zip_ref:
                for zip_info in zip_ref.infolist():
                    parts = zip_info.filename.split('/')
                    if zip_info.is_dir():
                        assert parts.pop() == ''
                        FolderModel.objects.create(
                            name=parts[-1],
                            parent=folder_obj.retrieve(parts[:-1]),
                            site=self.admin_site.name,
                            owner=request.user,
                        )
                        continue
                    filename = parts[-1]
                    mime_type, _ = mimetypes.guess_type(filename)
                    mime_type = mime_type or 'application/octet-stream'
                    proxy_model = FileModel.objects.get_model_for(mime_type)
                    extracted_file_obj = proxy_model.objects.create(
                        name=filename,
                        parent=folder_obj.retrieve(parts[:-1]),
                        file_name=proxy_model.generate_filename(filename),
                        mime_type=mime_type,
                        file_size=zip_info.file_size,
                    )
                    (default_storage.base_location / extracted_file_obj.folder_path).mkdir(parents=True, exist_ok=True)
                    sha1 = hashlib.sha1()
                    with zip_ref.open(zip_info.filename) as zip_entry, extracted_file_obj.open('wb+') as destination:
                        for chunk in zip_entry:
                            sha1.update(chunk)
                            destination.file.write(chunk)
                    extracted_file_obj.sha1 = sha1.hexdigest()
                    extracted_file_obj.save(update_fields=['sha1'])
        except Exception as exc:
            msg = gettext("Failed to extract archive “{name}”. Reason: {error}.")
            return HttpResponseBadRequest(msg.format(name={zip_file_obj.name}, error=str(exc)), status=415)
        msg = gettext("Successfully extracted ZIP archive “{name}” to folder “{folder}”.")
        return HttpResponse(msg.format(name=zip_file_obj.name, folder=zip_file_obj.folder.name))

    def get_editor_settings(self, request, inode):
        settings = super().get_editor_settings(request, inode)
        settings.update(
            react_component='Archive',
            download_file=True,
        )
        return settings

    def get_menu_extension_settings(self, request):
        return {'component': 'Archive'}

    def get_menu_extension_urls(self):
        urls = super().get_menu_extension_urls()
        urls.append(
            path(
                '<uuid:folder_id>/archive',
                self.admin_site.admin_view(self.archive_selected),
            ),
        )
        return urls

admin.site.register(ArchiveModel, ArchiveAdmin)
