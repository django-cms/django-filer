import json

from django.contrib import admin
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ValidationError
from django.db.models.expressions import F, Value
from django.db.models.fields import BooleanField
from django.db.models.functions import Lower
from django.http.response import HttpResponseBadRequest, HttpResponseNotFound, HttpResponseRedirect, JsonResponse
from django.middleware.csrf import get_token
from django.template.response import TemplateResponse
from django.urls import path, reverse

from finder.models.file import AbstractFileModel, InodeModel
from finder.models.folder import FolderModel, PinnedFolder, RealmModel


class InodeAdmin(admin.ModelAdmin):
    extra_data_fields = ['owner_name', 'is_folder', 'parent']
    sorting_map = {
        'name_asc': (InodeModel, Lower('name').asc(), lambda inode: inode['name'].lower(), False),
        'name_desc': (InodeModel, Lower('name').desc(), lambda inode: inode['name'].lower(), True),
        'date_asc': (InodeModel, 'last_modified_at', lambda inode: inode['last_modified_at'], False),
        'date_desc': (InodeModel, '-last_modified_at', lambda inode: inode['last_modified_at'], True),
        'size_asc': (AbstractFileModel, 'file_size', lambda inode: inode.get('file_size', 0), False),
        'size_desc': (AbstractFileModel, '-file_size', lambda inode: inode.get('file_size', 0), True),
        'type_asc': (AbstractFileModel, 'mime_type', lambda inode: inode.get('mime_type', ''), False),
        'type_desc': (AbstractFileModel, '-mime_type', lambda inode: inode.get('mime_type', ''), True),
    }

    def get_urls(self):
        urls = [
            path(
                '<uuid:folder_id>/toggle_pin',
                self.admin_site.admin_view(self.toggle_pin),
            ),
        ]
        urls.extend(super().get_urls())
        return urls

    def get_object(self, request, object_id, from_field=None):
        site = get_current_site(request)
        for model in InodeModel.real_models:
            try:
                obj = model.objects.get(id=object_id)
                if obj.is_folder and obj.realm.site == site and obj.realm.slug == self.admin_site.name:
                    return obj
                elif obj.folder.realm.site == site and obj.folder.realm.slug == self.admin_site.name:
                    return obj.casted
            except model.DoesNotExist:
                pass

    def check_for_valid_post_request(self, request, folder_id):
        if request.method != 'POST':
            return HttpResponseBadRequest(f"Method {request.method} not allowed. Only POST requests are allowed.")
        if request.content_type != 'application/json':
            return HttpResponseBadRequest(f"Invalid content-type {request.content_type}. Only application/json is allowed.")
        if self.get_object(request, folder_id) is None:
            return HttpResponseNotFound(f"Folder with id “{folder_id}” not found.")

    def toggle_pin(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        body = json.loads(request.body)
        current_folder = self.get_object(request, folder_id)
        if not (pinned_id := body.get('pinned_id')):
            return HttpResponseBadRequest("No pinned_id provided.")
        pinned_folder, created = PinnedFolder.objects.get_or_create(owner=request.user, folder_id=pinned_id)
        if created:
            request.session['finder_last_folder_id'] = None
        else:
            parent_folder = pinned_folder.folder.parent
            pinned_folder.delete()
            if str(folder_id) == pinned_id:
                return JsonResponse({
                    'success_url': reverse(
                        'admin:finder_inodemodel_change',
                        args=(parent_folder.id,),
                        current_app=self.admin_site.name,
                    ),
                })
        return JsonResponse({
            'favorite_folders': self.get_favorite_folders(request, current_folder),
        })

    def serialize_inode(self, inode):
        data = {field: inode.serializable_value(field) for field in inode.data_fields}
        data.update(
            owner_name=inode.owner.username if inode.owner else None,
            is_folder=inode.is_folder,
            change_url=reverse(
                'admin:finder_inodemodel_change',
                args=(inode.id,),
                current_app=self.admin_site.name,
            ),
            download_url=inode.get_download_url(),
            thumbnail_url=inode.get_thumbnail_url(),
            summary=inode.summary,
        )
        if (inode.is_folder):
            data.update(is_root=inode.is_root)
        return data

    def get_realm(self, request):
        realm, _ = RealmModel.objects.get_or_create(site=get_current_site(request), slug=self.admin_site.name)
        return realm

    def get_root_folder(self, request):
        return FolderModel.objects.get_root_folder(self.get_realm(request))

    def get_trash_folder(self, request):
        return FolderModel.objects.get_trash_folder(self.get_realm(request), request.user)

    def get_fallback_folder(self, request):
        realm = self.get_realm(request)
        try:
            last_folder_id = request.session['finder_last_folder_id']
            return FolderModel.objects.get(id=last_folder_id, realm=realm)
        except (FolderModel.DoesNotExist, KeyError):
            return FolderModel.objects.get_root_folder(realm)

    def get_inodes(self, request, sorting=None, **lookup):
        """
        Return a serialized list of file/folder-s for the given folder.
        """
        inodes, applicable_sorting = [], []
        for inode_model in InodeModel.real_models:
            queryset = (
                inode_model.objects.select_related('owner')
                .filter(**lookup)
                .annotate(owner_name=F('owner__username'))
                .annotate(is_folder=Value(inode_model.is_folder, output_field=BooleanField()))
            )
            data_fields = inode_model.data_fields + self.extra_data_fields
            if applicable_sorting := self.sorting_map.get(sorting):
                if issubclass(inode_model, applicable_sorting[0]):
                    queryset = queryset.order_by(applicable_sorting[1])
            for obj in queryset:
                values = {
                    'parent': obj.parent.id,
                    'change_url': reverse(
                        'admin:finder_inodemodel_change',
                        args=(obj.id,),
                        current_app=self.admin_site.name,
                    ),
                    'download_url': obj.get_download_url(),
                    'thumbnail_url': obj.casted.get_thumbnail_url(),
                    'summary': obj.casted.summary,
                }

                # search model admin for current inode and get its rendering settings
                if model_admin := self.admin_site._registry.get(obj.__class__):
                    values.update(model_admin.get_folderitem_settings(request, obj))

                values.update({field: obj.serializable_value(field) for field in data_fields if field not in values})
                inodes.append(values)

        if applicable_sorting:
            inodes.sort(key=applicable_sorting[2], reverse=applicable_sorting[3])
        return inodes

    def get_breadcrumbs(self, obj):
        breadcrumbs = [{
            'link': reverse(
                'admin:finder_inodemodel_change',
                args=(folder.id,),
                current_app=self.admin_site.name,
            ),
            'name': str(folder),
        } for folder in obj.ancestors]
        breadcrumbs.reverse()
        return breadcrumbs

    def get_favorite_folders(self, request, current_folder):
        realm = self.get_realm(request)
        folders = PinnedFolder.objects.filter(
            owner=request.user,
            folder__realm__id=realm.id,
        ).values(
            'folder__id',
            'folder__name',
        ).annotate(
            id=F('folder__id'),
            name=F('folder__name'),
            is_pinned=Value(True, output_field=BooleanField()),
        ).values('id', 'name', 'is_pinned')
        folders = [dict(
            **values,
            change_url=reverse(
                'admin:finder_inodemodel_change',
                args=(values['id'],),
                current_app=self.admin_site.name,
            ),
        ) for values in folders]
        fallback_folder = self.get_fallback_folder(request)
        root_folder = self.get_root_folder(request)
        trash_folder = self.get_trash_folder(request)
        for folder in folders:
            if folder['id'] == current_folder.id:
                if len(folders) == 0:
                    folders.append(self.serialize_inode(fallback_folder))
                break
        else:
            if current_folder.id == root_folder.id:
                folders.insert(0, self.serialize_inode(current_folder))
            elif current_folder.id != trash_folder.id:
                folders.append(self.serialize_inode(current_folder))
        if trash_folder.num_children > 0:
            inode_data = self.serialize_inode(trash_folder)
            inode_data.update(is_trash=True)
            folders.append(inode_data)
        return folders

    def changelist_view(self, request, extra_context=None):
        # always redirect the list view to the detail view of either the last used, or the root folder
        fallback_folder = self.get_fallback_folder(request)
        return HttpResponseRedirect(reverse(
            'admin:finder_inodemodel_change',
            args=(fallback_folder.id,),
            current_app=self.admin_site.name,
        ))

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        context.update(
            breadcrumbs=self.get_breadcrumbs(obj),
            finder_settings=self.get_editor_settings(request, obj),
        )
        return TemplateResponse(
            request,
            self.form_template,
            context,
        )

    def get_editor_settings(self, request, inode):
        favorite_folders = self.get_favorite_folders(request, inode.folder)
        settings = {
            'name': inode.name,
            'is_folder': inode.is_folder,
            'folder_id': inode.folder.id,
            'favorite_folders': favorite_folders,
            'csrf_token': get_token(request),
            'parent_id': inode.parent_id,
        }
        if inode.parent_id:
            settings['parent_url'] = reverse(
                'admin:finder_inodemodel_change',
                args=(inode.parent_id,),
                current_app=self.admin_site.name,
            )
        else:
            settings['parent_url'] = None
        return settings

    def get_folderitem_settings(self, request, inode):
        return {}

    def get_menu_extension_settings(self, request):
        """
        Hook to return the React context for extending menu items specific to this model.
        """
        return {}

