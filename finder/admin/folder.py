import json

from django.contrib import admin
from django.contrib.staticfiles.storage import staticfiles_storage
from django.core.exceptions import ObjectDoesNotExist, ValidationError, PermissionDenied
from django.db import transaction
from django.db.models import QuerySet, Subquery
from django.db.models.expressions import Value
from django.db.models.fields import BooleanField
from django.forms.widgets import Media
from django.http.response import (
    HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, HttpResponseNotAllowed, HttpResponseNotFound,
    JsonResponse,
)
from django.urls import path, reverse
from django.utils.translation import gettext
from django.utils.html import format_html

from finder.admin.inode import InodeAdmin
from finder.lookups import lookup_by_read_permission, lookup_by_tag
from finder.models.file import InodeModel, FileModel
from finder.models.folder import FolderModel, PinnedFolder
from finder.models.inode import DiscardedInode, InodeManager, filename_validator
from finder.models.filetag import FileTag
from finder.models.permission import Privilege, AccessControlEntry


@admin.register(FolderModel)
class FolderAdmin(InodeAdmin):
    form_template = 'finder/admin/change_folder_form.html'
    _model_admin_cache = {}

    @property
    def media(self):
        return Media(
            css={'all': ['finder/css/finder-admin.css']},
            js=[format_html(
                '<script type="module" src="{}"></script>',
                staticfiles_storage.url('finder/js/folder-admin.js')
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
                '<uuid:folder_id>/reorder',
                self.admin_site.admin_view(self.reorder_inodes),
            ),
            path(
                '<uuid:folder_id>/delete',
                self.admin_site.admin_view(self.delete_inodes),
            ),
            path(
                '<uuid:folder_id>/update_tags',
                self.admin_site.admin_view(self.update_tags),
            ),
            path(
                '<uuid:trash_folder_id>/undo_discard',
                self.admin_site.admin_view(self.undo_discarded_inodes),
            ),
            path(
                '<uuid:trash_folder_id>/erase_trash_folder',
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

    def change_view(self, request, inode_id, **kwargs):
        try:
            inode_obj = self.get_object(request, inode_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound(f"InodeModel<{inode_id}> not found.")

        if inode_obj.is_folder:
            return super().change_view(request, str(inode_id), **kwargs)

        # inode_obj is a file and hence we look for the specialized model admin
        model_admin = self.get_model_admin(inode_obj.mime_type)
        return model_admin.change_view(request, str(inode_id), **kwargs)

    def get_editor_settings(self, request, inode):
        settings = super().get_editor_settings(request, inode)
        trash_folder = self.get_trash_folder(request)
        ambit = request._ambit
        if inode.id != trash_folder.id:
            folder_url = self.get_inode_url(ambit.slug, str(inode.folder.id))
            if isinstance(inode.ancestors, QuerySet):
                if request.user.is_superuser:
                    can_change = Value(True, output_field=BooleanField())
                    can_view = Value(True, output_field=BooleanField())
                else:
                    can_change = AccessControlEntry.objects.privilege_subquery_exists(request.user, Privilege.WRITE)
                    can_view = AccessControlEntry.objects.privilege_subquery_exists(request.user, Privilege.READ)
                values = 'id', 'can_change', 'can_view'
                ancestors = list(inode.ancestors.annotate(can_change=can_change, can_view=can_view).values(*values))
            else:
                ancestors = [
                    {
                        'id': ancestor.id,
                        'can_change': ancestor.has_permission(request.user, Privilege.WRITE),
                        'can_view': ancestor.has_permission(request.user, Privilege.READ),
                    } for ancestor in inode.ancestors
                ]
            settings.update(
                is_root=inode.is_root,
                is_trash=False,
                is_admin=inode.has_permission(request.user, Privilege.ADMIN),
                can_change=inode.has_permission(request.user, Privilege.WRITE),
            )
            if FileTag.objects.exists():
                settings['tags'] = [
                    {'value': id, 'label': label, 'color': color}
                    for id, label, color in FileTag.objects.filter(ambit=ambit).values_list('id', 'label', 'color')
                ]
            request.session['finder_last_folder_id'] = str(inode.id)
        else:  # editor settings for the trash folder
            folder_url = self.get_inode_url(ambit.slug, str(self.get_fallback_folder(request).id))
            ancestors = [{'id': trash_folder.id, 'can_change': True, 'can_view': True}]
            settings.update(
                is_root=False,
                is_trash=True,
                is_admin=False,
                can_change=True,
            )
        settings.update(
            base_url=reverse('admin:finder_foldermodel_changelist', current_app=self.admin_site.name),
            menu_extensions=self.get_menu_extension_settings(request),
            folder_url=folder_url,
            ancestors=ancestors,
            open_folder_icon_url=staticfiles_storage.url('finder/icons/folder-open.svg'),
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
        if request.method != 'GET':
            return HttpResponseNotAllowed(f"Method {request.method} not allowed. Only GET requests are allowed.")
        try:
            current_folder = self.get_object(request, folder_id)
            request._ambit = current_folder.get_ambit()
        except ObjectDoesNotExist:
            return HttpResponseNotFound(f"FolderModel<{folder_id}> not found.")
        lookup = {}
        if not current_folder.is_trash:
            lookup.update(**lookup_by_tag(request), **lookup_by_read_permission(request))
        if search_query := request.GET.get('q'):
            inode_qs = self.search_for_inodes(request, current_folder, search_query, **lookup)
        else:
            inode_qs = self.get_inodes(request, parent=current_folder, **lookup)
        return JsonResponse({
            'inodes': list(inode_qs),
        })

    def search_for_inodes(self, request, current_folder, search_query, **lookup):
        search_zone = request.COOKIES.get('django-finder-search-zone')
        if search_zone == 'everywhere':
            starting_folder = current_folder.get_root_folder()
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
            return HttpResponseNotAllowed(f"Method {request.method} not allowed. Only POST requests are allowed.")
        try:
            folder = self.get_object(request, folder_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound(f"FolderModel<{folder_id}> not found.")
        if request.content_type != 'multipart/form-data' or 'upload_file' not in request.FILES:
            return HttpResponse("Bad encoding type or missing payload.", status=415)
        ambit = folder.get_ambit()
        model = FileModel.objects.get_model_for(request.FILES['upload_file'].content_type)
        try:
            new_file = model.objects.create_from_upload(
                ambit,
                request.FILES['upload_file'],
                folder=folder,
                owner=request.user,
            )
        except PermissionDenied as exc:
            return HttpResponseForbidden(str(exc))
        else:
            return JsonResponse({'file_info': new_file.as_dict(ambit)})

    def update_inode(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        body = json.loads(request.body)
        try:
            inode_obj = self.get_object(request, body['id'])
        except (ObjectDoesNotExist, KeyError):
            return HttpResponseNotFound(f"InodeModel<id={body.get('id', '<missing>')}> not found.")
        current_folder = self.get_object(request, folder_id)
        ambit = current_folder.get_ambit()
        inode_name = body['name']
        try:
            filename_validator(inode_name)
        except ValidationError as exc:
            return HttpResponse(exc.messages[0], status=409)
        if current_folder.listdir(name=inode_name, is_folder=True).exists():
            msg = gettext("A folder named “{name}” already exists.")
            return HttpResponse(msg.format(name=inode_name), status=409)
        update_values = {}
        for field in self.get_fields(request, inode_obj):
            if field in body and body[field] != getattr(inode_obj, field):
                setattr(inode_obj, field, body[field])
                update_values[field] = body[field]
        if update_values:
            inode_obj.save(update_fields=list(update_values.keys()))
        return JsonResponse({
            'new_inode': self.serialize_inode(ambit, inode_obj),
            'favorite_folders': self.get_favorite_folders(request, current_folder),
        })

    def copy_inodes(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        body = json.loads(request.body)
        current_folder = self.get_object(request, folder_id)
        ordering = current_folder.get_max_ordering()
        inode_ids = body.get('inode_ids', [])
        for entry in FolderModel.objects.filter_unified(
            id__in=inode_ids,
            user=request.user,
            has_read_permission=True,
        ):
            proxy_obj = InodeManager.get_proxy_object(entry)
            try:
                ordering += 1
                proxy_obj.copy_to(request._ambit, request.user, current_folder, ordering=ordering)
            except RecursionError as exc:
                return HttpResponse(str(exc), status=409)
            except PermissionDenied as exc:
                return HttpResponseForbidden(str(exc))
        lookup = lookup_by_read_permission(request)
        return JsonResponse({
            'inodes': list(self.get_inodes(request, parent=current_folder, **lookup)),
        })

    def move_inodes(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        body = json.loads(request.body)
        current_folder = self.get_object(request, folder_id)
        if 'target_id' in body:
            if body['target_id'] == 'parent':
                target_folder = current_folder.parent
            else:
                try:
                    target_folder = self.get_object(request, body['target_id'])
                except FolderModel.DoesNotExist:
                    target_folder = None
            if not target_folder:
                msg = gettext("Folder named “{folder}” not found.")
                return HttpResponseNotFound(msg.format(folder=body['target_id']))
        else:
            target_folder = current_folder
        inode_ids = body.get('inode_ids', [])
        try:
            target_folder.move_inodes(request.user, inode_ids)
        except ValidationError as exc:
            return HttpResponse(exc.messages[0], status=409)
        except PermissionDenied as exc:
            return HttpResponseForbidden(str(exc))
        else:
            lookup = lookup_by_read_permission(request)
            return JsonResponse({
                'inodes': list(self.get_inodes(request, parent=target_folder, **lookup)),
            })

    def reorder_inodes(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        insert_after = request.COOKIES.get('django-finder-layout') in ['tiles', 'mosaic']
        body = json.loads(request.body)
        target_inode = FolderModel.objects.get_inode(id=body.get('target_id'))
        if not target_inode.parent.has_permission(request.user, Privilege.WRITE):
            msg = gettext("You do not have permission to reorder items in folder “{folder}”.")
            return HttpResponseForbidden(msg.format(folder=target_inode.parent.name))

        inode_ids = body.get('inode_ids', [])
        if not request.user.is_superuser:
            reorderable_inode_ids = set(
                map(str, AccessControlEntry.objects.get_privilege_queryset(request.user, Privilege.WRITE).filter(
                    inode__in=inode_ids
                ).values_list('inode', flat=True).distinct())
            )
            inode_ids = [id for id in inode_ids if id in reorderable_inode_ids]  # preserve the order of inode_ids
        with transaction.atomic():
            target_inode.parent.reorder(target_inode.id, inode_ids, insert_after)
        lookup = {**lookup_by_tag(request), **lookup_by_read_permission(request)}
        return JsonResponse({
            'inodes': list(self.get_inodes(request, parent=target_inode.parent, **lookup)),
        })

    def delete_inodes(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        user = request.user
        body = json.loads(request.body)
        current_folder = self.get_object(request, folder_id)
        trash_folder = self.get_trash_folder(request)
        if current_folder.id == trash_folder.id:
            return HttpResponse("Cannot move inodes from trash folder into itself.", status=409)
        if not current_folder.has_permission(user, Privilege.WRITE):
            msg = gettext("You do not have permission to delete items from folder “{folder}”.")
            return HttpResponseForbidden(msg.format(folder=current_folder.name))

        deleted_inodes = []
        trash_ordering = trash_folder.get_max_ordering()
        inode_ids = body.get('inode_ids', [])
        with transaction.atomic():
            for entry in FolderModel.objects.filter_unified(user=user, has_write_permission=True, id__in=inode_ids):
                inode = FolderModel.objects.get_inode(id=entry['id'])
                if entry['is_folder']:
                    PinnedFolder.objects.filter(folder=inode).delete()
                    while trash_folder.listdir(name=inode.name, is_folder=True).exists():
                        inode.name = f"{inode.name}.renamed"
                DiscardedInode.objects.create(
                    inode=inode.id,
                    previous_parent=inode.parent,
                )
                trash_ordering += 1
                inode.ordering = trash_ordering
                inode.parent = trash_folder
                deleted_inodes.append(inode)
            for model in InodeModel.get_models(include_folder=True):
                model.objects.bulk_update(
                    filter(lambda obj: isinstance(obj, model), deleted_inodes),
                    ['name', 'ordering', 'parent'] if model.is_folder else ['ordering', 'parent'],
                )
            AccessControlEntry.objects.filter(inode__in=[d.id for d in deleted_inodes]).delete()
            current_folder.reorder()

        return JsonResponse({
            'favorite_folders': self.get_favorite_folders(request, current_folder),
        })

    def update_tags(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        ambit = request._ambit
        if not ambit.root_folder.has_permission(request.user, Privilege.ADMIN):
            msg = gettext("You do not have permission to edit tags.")
            return HttpResponseForbidden(msg)

        CREATE_TAG = object()
        body = json.loads(request.body)
        preserved_tag_ids = []
        with transaction.atomic():
            for tag in body['tags']:
                id = tag.get('value', CREATE_TAG)
                if id is CREATE_TAG:
                    create_kwargs = {'ambit': ambit, 'label': tag['label'], 'color': tag['color']}
                    created_entry = FileTag.objects.create(**create_kwargs)
                    preserved_tag_ids.append(created_entry.id)
                else:
                    update_entry = FileTag.objects.get(id=id, ambit=ambit)
                    update_fields = []
                    if update_entry.label != tag['label']:
                        update_entry.label = tag['label']
                        update_fields.append('label')
                    if update_entry.color != tag['color']:
                        update_entry.color = tag['color']
                        update_fields.append('color')
                    if update_fields:
                        update_entry.save(update_fields=update_fields)
                    preserved_tag_ids.append(update_entry.id)
            FileTag.objects.filter(ambit=ambit).exclude(id__in=preserved_tag_ids).delete()
        return JsonResponse({
            'tags': [
                {'value': id, 'label': label, 'color': color}
                for id, label, color in FileTag.objects.filter(ambit=ambit).values_list('id', 'label', 'color')
            ],
        })

    def undo_discarded_inodes(self, request, trash_folder_id):
        if response := self.check_for_valid_post_request(request, trash_folder_id):
            return response
        body = json.loads(request.body)
        trash_folder = self.get_trash_folder(request)
        if trash_folder.id != trash_folder_id:
            return HttpResponseBadRequest(f"Trash folder with ID=“{trash_folder.id}” expected.")
        discarded_inodes = DiscardedInode.objects.filter(inode__in=body.get('inode_ids', []))
        restored_inodes, restored_folders = [], {}
        with transaction.atomic():
            for entry in trash_folder.listdir(id__in=Subquery(discarded_inodes.values('inode'))):
                inode = FolderModel.objects.get_inode(id=entry['id'])
                previous_parent = discarded_inodes.get(inode=inode.id).previous_parent
                if not previous_parent.has_permission(request.user, Privilege.WRITE):
                    msg = gettext("You do not have permission to restore item “{item}” to folder “{folder}”.")
                    raise PermissionDenied(msg.format(item=inode.name, folder=previous_parent.name))
                while previous_parent.listdir(name=inode.name, is_folder=True).exists():
                    inode.name = f"{inode.name}.renamed"
                if previous_parent.id in restored_folders:
                    restored_folders[previous_parent.id] += 1
                else:
                    restored_folders[previous_parent.id] = previous_parent.get_max_ordering() + 1
                inode.ordering = restored_folders[previous_parent.id]
                inode.parent = previous_parent
                inode.transfer_access_control_list(previous_parent)
                restored_inodes.append(inode)
            for model in InodeModel.get_models(include_folder=True):
                model.objects.bulk_update(
                    filter(lambda obj: isinstance(obj, model), restored_inodes),
                    ['name', 'ordering', 'parent'] if model.is_folder else ['ordering', 'parent'],
                )
            discarded_inodes.delete()
            trash_folder.reorder()
        return HttpResponse(status=204)  # No content

    def erase_trash_folder(self, request, trash_folder_id):
        if request.method != 'DELETE':
            return HttpResponseNotAllowed(f"Method {request.method} not allowed. Only DELETE requests are allowed.")
        trash_folder = FolderModel.objects.get(id=trash_folder_id, owner=request.user)
        request._ambit = trash_folder.get_ambit()
        trash_folder_entries = trash_folder.listdir()
        with transaction.atomic():
            DiscardedInode.objects.filter(inode__in=list(trash_folder_entries.values_list('id', flat=True))).delete()
            for entry in trash_folder_entries:
                # bulk delete does not work here because each file must be erased from disk
                proxy_obj = InodeManager.get_proxy_object(entry)
                if proxy_obj.is_folder:
                    proxy_obj.delete()
                else:
                    proxy_obj.erase_and_delete(request._ambit)
        fallback_folder = self.get_fallback_folder(request)
        success_url = self.get_inode_url(request._ambit.slug, str(fallback_folder.id))
        return JsonResponse({'success_url': success_url})

    def add_folder(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        parent_folder = self.get_object(request, folder_id)
        if not parent_folder.has_permission(request.user, Privilege.WRITE):
            return HttpResponseForbidden("Permission denied to create a new folder.")
        body = json.loads(request.body)
        if parent_folder.listdir(name=body['name'], is_folder=True).exists():
            msg = gettext("A folder named “{name}” already exists.")
            return HttpResponse(msg.format(name=body['name']), status=409)
        new_folder = FolderModel.objects.create(
            name=body['name'],
            parent=parent_folder,
            owner=request.user,
            ordering=parent_folder.get_max_ordering() + 1,
        )
        new_folder.transfer_access_control_list(parent_folder)
        return JsonResponse({'new_folder': self.serialize_inode(request._ambit, new_folder)})

    def get_or_create_folder(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        parent_folder = self.get_object(request, folder_id)
        if not parent_folder.has_permission(request.user, Privilege.WRITE):
            return HttpResponseForbidden("Permission denied to create a folder through recursive upload.")
        ambit = parent_folder.get_ambit()
        ordering = parent_folder.get_max_ordering() + 1
        body = json.loads(request.body)
        for folder_name in body['relative_path'].split('/'):
            folder, created = FolderModel.objects.get_or_create(
                name=folder_name,
                parent=parent_folder,
                defaults={'owner': request.user, 'ordering': ordering},
            )
            if created:
                ordering += 1
                folder.transfer_access_control_list(parent_folder)
        return JsonResponse({'folder': self.serialize_inode(ambit, folder)})
