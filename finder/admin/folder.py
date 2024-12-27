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
from finder.models.inode import DiscardedInode, InodeManager, filename_validator
from finder.models.label import Label

from .inode import InodeAdmin


@admin.register(FolderModel)
class FolderAdmin(InodeAdmin):
    form_template = 'finder/admin/change_folder_form.html'
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
            css={'all': ['finder/css/finder-admin.css']},
            js=[format_html(
                '<script type="module" src="{}"></script>', static('finder/js/folder-admin.js')
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
                self.admin_site.admin_view(self.upload_file),
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
            path(
                '<uuid:folder_id>/get_or_create_folder',
                self.admin_site.admin_view(self.get_or_create_folder),
            ),
        ]
        urls.extend(default_urls)
        for model in InodeModel.get_models(include_proxy=True):
            if model_admin := self.admin_site._registry.get(model):
                urls.extend(model_admin.get_menu_extension_urls())
        return urls

    def has_add_permission(self, request):
        return False

    def change_view(self, request, inode_id, **kwargs):
        inode_obj = self.get_object(request, inode_id)
        if inode_obj is None:
            return self._get_obj_does_not_exist_redirect(request, self.model._meta, str(inode_id))
        if inode_obj.is_folder:
            return super().change_view(request, str(inode_id), **kwargs)

        # inode_obj is a file and hence we look for the specialized model admin
        model_admin = self.get_model_admin(inode_obj.mime_type)
        return model_admin.change_view(request, str(inode_id), **kwargs)

    def get_editor_settings(self, request, inode):
        settings = super().get_editor_settings(request, inode)
        trash_folder = self.get_trash_folder(request)
        if inode.id != trash_folder.id:
            settings.update(
                is_root=inode.is_root,
                is_trash=False,
                folder_url=reverse(
                    'admin:finder_inodemodel_change',
                    args=(inode.folder.id,),
                    current_app=self.admin_site.name,
                ),
            )
            if Label.objects.exists():
                settings['labels'] = [
                    {'value': id, 'label': name, 'color': color}
                    for id, name, color in Label.objects.values_list('id', 'name', 'color')
                ]
            request.session['finder_last_folder_id'] = str(inode.id)
        else:
            settings.update(
                is_root=False,
                is_trash=True,
                folder_url=reverse(
                    'admin:finder_inodemodel_change',
                    args=(self.get_fallback_folder(request).id,),
                    current_app=self.admin_site.name,
                ),
            )
        if isinstance(inode.ancestors, QuerySet):
            ancestor_ids = list(inode.ancestors.values_list('id', flat=True))
        else:
            ancestor_ids = [ancestor.id for ancestor in inode.ancestors]
        settings.update(
            base_url=reverse('admin:finder_foldermodel_changelist', current_app=self.admin_site.name),
            ancestors=ancestor_ids,
            legends=self._legends,
            menu_extensions=self.get_menu_extension_settings(request),
        )
        return settings

    def get_menu_extension_settings(self, request):
        extensions = []
        for model in InodeModel.get_models(include_proxy=True):
            if model_admin := self.admin_site._registry.get(model):
                    extension = model_admin.get_menu_extension_settings(request)
                    if extension.get('component'):
                        extensions.append(extension)
        return extensions

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
        if search_query := request.GET.get('q'):
            inode_qs = self.search_for_inodes(request, current_folder, search_query)
        else:
            inode_qs = self.get_inodes(request, parent=current_folder)
        return JsonResponse({
            'inodes': list(inode_qs),
        })

    def search_for_inodes(self, request, current_folder, search_query, **lookup):
        search_realm = request.COOKIES.get('django-finder-search-realm')
        if search_realm == 'everywhere':
            starting_folder = self.get_realm(request).root_folder
        else:
            starting_folder = current_folder
        if isinstance(starting_folder.descendants, QuerySet):
            parent_ids = Subquery(starting_folder.descendants.values('id'))
        else:
            parent_ids = [descendant.id for descendant in starting_folder.descendants]
        return self.get_inodes(
            request,
            parent_id__in=parent_ids,
            name__icontains=search_query,
            **lookup,
        )

    def upload_file(self, request, folder_id):
        if request.method != 'POST':
            return HttpResponseBadRequest(f"Method {request.method} not allowed. Only POST requests are allowed.")
        if not (folder := self.get_object(request, folder_id)):
            return HttpResponseNotFound(f"Folder {folder_id} not found.")
        if request.content_type != 'multipart/form-data' or 'upload_file' not in request.FILES:
            return HttpResponseBadRequest("Bad encoding type or missing payload.")
        model = FileModel.objects.get_model_for(request.FILES['upload_file'].content_type)
        new_file = model.objects.create_from_upload(
            request.FILES['upload_file'],
            folder=folder,
            owner=request.user,
        )
        return JsonResponse({'file_info': new_file.as_dict})

    def update_inode(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        body = json.loads(request.body)
        try:
            obj = self.get_object(request, body['id'])
        except (InodeModel.DoesNotExist, KeyError):
            return HttpResponseNotFound(f"Inode(id={body.get('id', '<missing>')}) not found.")
        current_folder = self.get_object(request, folder_id)
        inode_name = body['name']
        try:
            filename_validator(inode_name)
        except ValidationError as exc:
            return HttpResponseBadRequest(exc.message, status=409)
        if current_folder.listdir(name=inode_name, is_folder=True).exists():
            msg = gettext("A folder named “{name}” already exists.")
            return HttpResponseBadRequest(msg.format(name=inode_name), status=409)
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
        for values in FolderModel.objects.filter_unified(id__in=inode_ids):
            inode = FolderModel.objects.get_inode(id=values['id'])
            try:
                inode.copy_to(current_folder, owner=request.user)
            except RecursionError as exc:
                return HttpResponseBadRequest(str(exc), status=409)
        return JsonResponse({
            'inodes': list(self.get_inodes(request, parent=current_folder)),
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
            for entry in FolderModel.objects.filter_unified(id__in=inode_ids):
                try:
                    DiscardedInode.objects.get(inode=entry['id']).delete()
                except DiscardedInode.DoesNotExist:
                    pass
                proxy_obj = InodeManager.get_proxy_object(entry)
                proxy_obj.parent = target_folder
                proxy_obj.validate_constraints()
                proxy_obj._meta.model.objects.filter(id=entry['id']).update(parent=target_folder)
        except ValidationError as e:
            return HttpResponseBadRequest(e.message, status=409)
        return JsonResponse({
            'inodes': list(self.get_inodes(request, parent=target_folder)),
        })

    def delete_inodes(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        body = json.loads(request.body)
        current_folder = self.get_object(request, folder_id)
        trash_folder = self.get_trash_folder(request)
        if current_folder.id == trash_folder.id:
            return HttpResponseBadRequest("Cannot move inodes from trash folder into itself.")
        inode_ids = body.get('inode_ids', [])
        for entry in FolderModel.objects.filter_unified(id__in=inode_ids):
            inode = FolderModel.objects.get_inode(id=entry['id'])
            if entry['is_folder']:
                PinnedFolder.objects.filter(folder=inode).delete()
                while trash_folder.listdir(name=inode.name, is_folder=True).exists():
                    inode.name = f"{inode.name}.renamed"
                inode.save(update_fields=['name'])
            DiscardedInode.objects.create(
                inode=inode.id,
                previous_parent=inode.parent,
            )
            inode.parent = trash_folder
            inode.save(update_fields=['parent'])
        return JsonResponse({
            'favorite_folders': self.get_favorite_folders(request, current_folder),
        })

    def undo_discarded_inodes(self, request):
        if request.method != 'POST':
            return HttpResponseBadRequest(f"Method {request.method} not allowed. Only POST requests are allowed.")
        body = json.loads(request.body)
        trash_folder = self.get_trash_folder(request)
        discarded_inodes = DiscardedInode.objects.filter(inode__in=body.get('inode_ids', []))
        for entry in trash_folder.listdir(id__in=Subquery(discarded_inodes.values('inode'))):
            inode = FolderModel.objects.get_inode(id=entry['id'])
            inode.parent = discarded_inodes.get(inode=inode.id).previous_parent
            inode.save(update_fields=['parent'])
        discarded_inodes.delete()
        return HttpResponse()

    def erase_trash_folder(self, request):
        if request.method != 'DELETE':
            return HttpResponseBadRequest(f"Method {request.method} not allowed. Only DELETE requests are allowed.")
        trash_folder_entries = self.get_trash_folder(request).listdir()
        DiscardedInode.objects.filter(inode__in=list(trash_folder_entries.values_list('id', flat=True))).delete()
        for entry in trash_folder_entries:
            # bulk delete does not work here because file must be erased from disk
            proxy_obj = InodeManager.get_proxy_object(entry)
            proxy_obj.delete()
        fallback_folder = self.get_fallback_folder(request)
        return JsonResponse({
            'success_url': reverse(
                'admin:finder_inodemodel_change',
                args=(fallback_folder.id,),
            ),
        })

    def add_folder(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        if not (parent_folder := self.get_object(request, folder_id)):
            return HttpResponseNotFound(f"Folder {folder_id} not found.")
        body = json.loads(request.body)
        if parent_folder.listdir(name=body['name'], is_folder=True).exists():
            msg = gettext("A folder named “{name}” already exists.")
            return HttpResponseBadRequest(msg.format(name=body['name']), status=409)
        new_folder = FolderModel.objects.create(
            name=body['name'],
            parent=parent_folder,
            owner=request.user,
        )
        return JsonResponse({'new_folder': self.serialize_inode(new_folder)})

    def get_or_create_folder(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        if not (folder := self.get_object(request, folder_id)):
            return HttpResponseNotFound(f"Folder {folder_id} not found.")
        body = json.loads(request.body)
        for folder_name in body['relative_path'].split('/'):
            folder, _ = FolderModel.objects.get_or_create(
                name=folder_name,
                parent=folder,
                defaults={'owner': request.user},
            )
        return JsonResponse({'folder': self.serialize_inode(folder)})
