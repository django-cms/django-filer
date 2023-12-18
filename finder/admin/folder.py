import json

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models import QuerySet, Subquery

from django.forms.widgets import Media
from django.http.response import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, JsonResponse
from django.templatetags.static import static
from django.urls import path, reverse
from django.utils.translation import gettext, gettext_lazy as _
from django.utils.html import format_html

from finder.models.file import InodeModel, FileModel
from finder.models.folder import FolderModel, PinnedFolder
from finder.models.inode import DiscardedInode

from .inode import InodeAdmin


@admin.register(FolderModel)
class FolderAdmin(InodeAdmin):
    form_template = 'admin/finder/change_folder_form.html'
    _model_admin_cache = {}
    _legends = {
        'name': _("Name"),
        'owner_name': _("Owner"),
        'details': _("Details"),
        'created_at': _("Created at"),
        'mime_type': _("Mime type"),
    }

    @property
    def media(self):
        return Media(
            css={'all': ['admin/finder/css/finder-admin.css']},
            js=[format_html(
                '<script type="module" src="{}"></script>', static('admin/finder/js/folder-admin.js')
            )],
        )

    def get_urls(self):
        filtered_views = ['finder.admin.folder.FolderAdmin.change_view', 'django.views.generic.base.RedirectView']
        default_urls = filter(lambda p: p.lookup_str not in filtered_views, super().get_urls())
        urls = [
            path(
                '<uuid:inode_id>',
                self.admin_site.admin_view(self.change_view),
                name='finder_inodemodel_change',
            ),
            path(
                '<uuid:folder_id>/fetch',
                self.admin_site.admin_view(self.fetch_inodes),
            ),
            path(
                '<uuid:folder_id>/upload',
                self.admin_site.admin_view(self.upload_files),
            ),
            path(
                '<uuid:folder_id>/update',
                self.admin_site.admin_view(self.update_inode),
            ),
            path(
                '<uuid:folder_id>/copy',
                self.admin_site.admin_view(self.copy_inodes),
            ),
            path(
                '<uuid:folder_id>/move',
                self.admin_site.admin_view(self.move_inodes),
            ),
            path(
                '<uuid:folder_id>/delete',
                self.admin_site.admin_view(self.delete_inodes),
            ),
            path(
                'undo_discard',
                self.admin_site.admin_view(self.undo_discarded_inodes),
            ),
            path(
                'erase_trash_folder',
                self.admin_site.admin_view(self.erase_trash_folder),
            ),
            path(
                '<uuid:folder_id>/add_folder',
                self.admin_site.admin_view(self.add_folder),
            ),
        ]
        urls.extend(default_urls)
        return urls

    def has_add_permission(self, request):
        return False

    def change_view(self, request, inode_id, **kwargs):
        inode_obj = self.get_object(request, inode_id)
        if inode_obj is None:
            return self._get_obj_does_not_exist_redirect(request, self.model._meta, inode_id)
        if inode_obj.is_folder:
            return super().change_view(request, str(inode_id), **kwargs)

        # inode_obj is a file and hence we look for the specialized model admin
        model_admin = self.get_model_admin(inode_obj.mime_type)
        return model_admin.change_view(request, str(inode_id), **kwargs)

    def get_settings(self, request, inode):
        settings = super().get_settings(request, inode)
        if isinstance(inode.ancestors, QuerySet):
            ancestor_ids = list(inode.ancestors.values_list('id', flat=True))
        else:
            ancestor_ids = [ancestor.id for ancestor in inode.ancestors]
        settings.update(
            ancestors=ancestor_ids,
            legends=self._legends,
        )
        return settings

    def get_object(self, request, object_id, from_field=None):
        for model in InodeModel.all_models:
            try:
                obj = model.objects.get(id=object_id)
                if obj.is_folder and obj.site == self.admin_site.name:
                    return obj
                elif obj.folder.site == self.admin_site.name:
                    return obj
            except model.DoesNotExist:
                pass

    def get_model_admin(self, mime_type):
        if model_admin := self._model_admin_cache.get(mime_type):
            return model_admin
        for model, model_admin in self.admin_site._registry.items():
            if model._meta.app_label == 'finder':
                if mime_type in getattr(model, 'accept_mime_types', ()):
                    self._model_admin_cache[mime_type] = model_admin
                    break
        else:
            main_mime_type = '/'.join((mime_type.split('/')[0], '*'))
            for model, model_admin in self.admin_site._registry.items():
                if model._meta.app_label == 'finder':
                    if main_mime_type in getattr(model, 'accept_mime_types', ()):
                        self._model_admin_cache[mime_type] = model_admin
                        break
            else:
                # fallback to the default file admin
                self._model_admin_cache[mime_type] = self.admin_site._registry.get(FileModel)
        return self._model_admin_cache[mime_type]

    def fetch_inodes(self, request, folder_id):
        if not (current_folder := self.get_object(request, folder_id)):
            return HttpResponseNotFound(f"Folder {folder_id} not found.")
        sorting = request.COOKIES.get('django-finder-sorting')
        if query := request.GET.get('q'):
            search_realm = request.COOKIES.get('django-finder-search-realm')
            if search_realm == 'everywhere':
                starting_folder = FolderModel.objects.get_root_folder(self.admin_site.name)
            else:
                starting_folder = current_folder
            inodes = self.search_for_inodes(starting_folder, query, sorting=sorting)
        else:
            inodes = self.get_inodes(parent=current_folder, sorting=sorting)
        return JsonResponse({
            'inodes': inodes,
        })

    def search_for_inodes(self, starting_folder, query, sorting=None):
        if isinstance(starting_folder.descendants, QuerySet):
            parent_ids = Subquery(starting_folder.descendants.values('id'))
        else:
            parent_ids = [descendant.id for descendant in starting_folder.descendants]
        return self.get_inodes(
            sorting=sorting,
            parent_id__in=parent_ids,
            name__icontains=query,
        )

    def upload_files(self, request, folder_id):
        if request.method != 'POST':
            return HttpResponseBadRequest(f"Method {request.method} not allowed. Only POST requests are allowed.")
        if not (folder := self.get_object(request, folder_id)):
            return HttpResponseNotFound(f"Folder {folder_id} not found.")
        if request.content_type == 'multipart/form-data' and 'upload_file' in request.FILES:
            model = FileModel.objects.get_model_for(request.FILES['upload_file'].content_type)
            new_file = model.objects.create_from_upload(
                request.FILES['upload_file'],
                folder=folder,
                owner=request.user,
            )
        return HttpResponse(f"Uploaded {new_file.name} successfully.")

    def check_for_valid_post_request(self, request, folder_id):
        if request.method != 'POST':
            return HttpResponseBadRequest(f"Method {request.method} not allowed. Only POST requests are allowed.")
        if request.content_type != 'application/json':
            return HttpResponseBadRequest(f"Invalid content-type {request.content_type}. Only application/json is allowed.")
        if self.get_object(request, folder_id) is None:
            return HttpResponseNotFound(f"Folder with id “{folder_id}” not found.")

    def update_inode(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        body = json.loads(request.body)
        try:
            obj = self.get_object(request, body['id'])
        except (InodeModel.DoesNotExist, KeyError):
            return HttpResponseNotFound(f"Inode(id={body.get('id', '<missing>')}) not found.")
        current_folder = self.get_object(request, folder_id)
        if next(current_folder.listdir(name=body['name'], is_folder=True), None):
            msg = gettext("A folder named “{name}” already exists.")
            return HttpResponseBadRequest(msg.format(name=body['name']), status=409)
        update_values = {}
        for field in self.get_fields(request, obj):
            if field in body and body[field] != getattr(obj, field):
                setattr(obj, field, body[field])
                update_values[field] = body[field]
        if update_values:
            obj.save(update_fields=list(update_values.keys()))
        favorite_folders = self.get_favorite_folders(request, current_folder)
        if update_values:
            for folder in favorite_folders:
                if folder['id'] == obj.id:
                    folder.update(update_values)
                    break
        return JsonResponse({
            'new_inode': self.serialize_inode(obj),
            'favorite_folders': favorite_folders,
        })

    def copy_inodes(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        body = json.loads(request.body)
        current_folder = self.get_object(request, folder_id)
        inode_ids = body.get('inode_ids', [])
        for inode in FolderModel.objects.filter_inodes(id__in=inode_ids):
            inode.copy_to(current_folder, owner=request.user)
        return JsonResponse({
            'inodes': self.get_inodes(parent=current_folder),
        })

    def move_inodes(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        body = json.loads(request.body)
        current_folder = self.get_object(request, folder_id)
        if 'target_folder' in body:
            if not (target_folder := self.get_object(request, body['target_folder'])):
                msg = gettext("Folder named “{folder}” not found.")
                return HttpResponseNotFound(msg.format(folder=body['target_folder']))
        else:
            target_folder = current_folder
        try:
            inode_ids = body.get('inode_ids', [])
            for inode in FolderModel.objects.filter_inodes(id__in=inode_ids):
                try:
                    DiscardedInode.objects.get(inode=inode.id).delete()
                except DiscardedInode.DoesNotExist:
                    pass
                inode.parent = target_folder
                inode.validate_constraints()
                inode.save(update_fields=['parent'])
        except ValidationError as e:
            return HttpResponseBadRequest(e.message, status=409)
        return JsonResponse({
            'inodes': self.get_inodes(parent=target_folder),
        })

    def delete_inodes(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        body = json.loads(request.body)
        current_folder = self.get_object(request, folder_id)
        trash_folder = FolderModel.objects.get_trash_folder(self.admin_site.name, owner=request.user)
        if current_folder.id == trash_folder.id:
            return HttpResponseBadRequest("Cannot move inodes from trash folder into itself.")
        inode_ids = body.get('inode_ids', [])
        for inode in FolderModel.objects.filter_inodes(id__in=inode_ids):
            DiscardedInode.objects.create(
                inode=inode.id,
                previous_parent=inode.parent,
            )
            inode.parent = trash_folder
            inode.save(update_fields=['parent'])
            if inode.is_folder:
                PinnedFolder.objects.filter(folder=inode).delete()
        return JsonResponse({
            'favorite_folders': self.get_favorite_folders(request, current_folder),
        })

    def undo_discarded_inodes(self, request):
        if request.method != 'POST':
            return HttpResponseBadRequest(f"Method {request.method} not allowed. Only POST requests are allowed.")
        body = json.loads(request.body)
        trash_folder = FolderModel.objects.get_trash_folder(self.admin_site.name, owner=request.user)
        discarded_inodes = DiscardedInode.objects.filter(inode__in=body.get('inode_ids', []))
        for inode in trash_folder.listdir(id__in=Subquery(discarded_inodes.values('inode'))):
            inode.parent = discarded_inodes.get(inode=inode.id).previous_parent
            inode.save(update_fields=['parent'])
        discarded_inodes.delete()
        return HttpResponse()

    def erase_trash_folder(self, request):
        if request.method != 'DELETE':
            return HttpResponseBadRequest(f"Method {request.method} not allowed. Only DELETE requests are allowed.")
        trash_folder = FolderModel.objects.get_trash_folder(self.admin_site.name, owner=request.user)
        for inode in trash_folder.listdir():
            DiscardedInode.objects.get(inode=inode.id).delete()
            inode.delete()
        fallback_folder = self.get_fallback_folder(request)
        return JsonResponse({
            'success_url': reverse(
                'admin:finder_inodemodel_change',
                args=(fallback_folder.id,),
                current_app=self.admin_site.name,
            ),
        })

    def add_folder(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        body = json.loads(request.body)
        if not (parent_folder := self.get_object(request, folder_id)):
            return HttpResponseNotFound(f"Folder {folder_id} not found.")
        if next(parent_folder.listdir(name=body['name'], is_folder=True), None):
            msg = gettext("A folder named “{name}” already exists.")
            return HttpResponseBadRequest(msg.format(name=body['name']), status=409)
        new_folder = FolderModel.objects.create(
            name=body['name'],
            parent=parent_folder,
            site=self.admin_site.name,
            owner=request.user,
        )
        return JsonResponse({'new_folder': self.serialize_inode(new_folder)})
