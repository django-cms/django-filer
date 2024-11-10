import hashlib
import json
import mimetypes
import pathlib
import zipfile

from django.contrib import admin
from django.core.files.storage import default_storage
from django.http.response import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, JsonResponse
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

    def archive_selected(self, request, folder_id):
        if request.method != 'POST':
            return HttpResponseBadRequest(f"Method {request.method} not allowed. Only POST requests are allowed.")
        if not (folder_obj := self.get_object(request, folder_id)):
            return HttpResponseNotFound(f"Folder {folder_id} not found.")
        body = json.loads(request.body)
        if len(body.get('archive_name', '')) < 1 or len(body.get('inode_ids', [])) < 1:
            return HttpResponseBadRequest("Archive name and inode IDs are required")

        inode_objects = []
        for inode_id in body['inode_ids']:
            try:
                inode_obj = FolderModel.objects.get_inode(id=inode_id)
            except FolderModel.DoesNotExist:
                return HttpResponseBadRequest(f"Inode with ID “{inode_id}” not found")
            else:
                inode_objects.append(inode_obj)
                if inode_obj.is_folder:
                    for descendant in inode_obj.descendants:
                        inode_objects.extend(descendant.listdir())

        filename = self.model.generate_filename(body['archive_name'])
        filename = f'{filename}.zip' if not filename.endswith('.zip') else filename
        zip_file_obj = self.model.objects.create(
            name=body['archive_name'],
            parent=folder_obj,
            file_name=filename,
            mime_type='application/zip',
            owner=request.user,
            file_size=0,
        )
        (default_storage.base_location / zip_file_obj.file_path.parent).mkdir(parents=True, exist_ok=True)
        offset = len(folder_obj.ancestors)
        with zipfile.ZipFile(default_storage.path(zip_file_obj.file_path), 'w') as zip_ref:
            for inode_obj in inode_objects:
                ancestors = list(inode_obj.ancestors)
                ancestors.reverse()
                parts = [inode.name for inode in ancestors[offset:]]
                if inode_obj.is_folder:
                    zip_ref.mkdir('/'.join(parts))
                else:
                    parts.append(inode_obj.name)
                    zip_ref.write(default_storage.path(inode_obj.file_path), '/'.join(parts))
        zip_path = pathlib.Path(zip_ref.filename)
        zip_file_obj.file_size = zip_path.stat().st_size
        sha1 = hashlib.sha1()
        with zip_path.open('rb') as zip_file:
            for chunk in iter(lambda: zip_file.read(4096), b''):
                sha1.update(chunk)
        zip_file_obj.sha1 = sha1.hexdigest()
        zip_file_obj.save(update_fields=['file_size', 'sha1'])
        return JsonResponse({
            'new_file': self.serialize_inode(zip_file_obj),
        })

    def unarchive_file(self, request, file_id):
        if request.method != 'POST':
            return HttpResponseBadRequest(f"Method {request.method} not allowed. Only POST requests are allowed.")
        if not (zip_file_obj := self.get_object(request, file_id)):
            return HttpResponseNotFound(f"File {file_id} not found.")
        archive_name = pathlib.Path(zip_file_obj.name)
        if archive_name.suffix in ['.zip', '.tar', '.tar.gz', '.gz']:
            archive_name = archive_name.stem
        else:
            archive_name = str(archive_name)
        if FolderModel.objects.filter(
            name=archive_name,
            parent=zip_file_obj.folder,
        ).exists():
            msg = gettext("Can not extract archive. A folder named “{name}” already exists.")
            return HttpResponseBadRequest(msg.format(name=archive_name), status=409)
        try:
            folder_obj = FolderModel.objects.create(
                name=archive_name,
                parent=zip_file_obj.folder,
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
        settings.update(download_file=True)
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
