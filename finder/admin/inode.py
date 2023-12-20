import json

from django.contrib import admin
from django.core.exceptions import ValidationError
from django.db.models.expressions import F, Value
from django.db.models.fields import BooleanField
from django.db.models.functions import Lower
from django.http.response import HttpResponseBadRequest, HttpResponseRedirect, JsonResponse
from django.middleware.csrf import get_token
from django.template.response import TemplateResponse
from django.urls import path, reverse

from finder.models.file import AbstractFileModel, InodeModel
from finder.models.folder import FolderModel, PinnedFolder


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
        for model in InodeModel.all_models:
            try:
                obj = model.objects.get(id=object_id)
                if obj.is_folder and obj.site == self.admin_site.name:
                    return obj
                elif obj.folder.site == self.admin_site.name:
                    return obj
            except model.DoesNotExist:
                pass

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

    def get_fallback_folder(self, request):
        try:
            last_folder_id = request.session['finder_last_folder_id']
            return FolderModel.objects.get(id=last_folder_id, site=self.admin_site.name)
        except (FolderModel.DoesNotExist, KeyError, ValidationError):
            return FolderModel.objects.get_root_folder(self.admin_site.name)

    def get_inodes(self, sorting=None, **lookup):
        """
        Return a serialized list of file/folder-s for the given folder.
        """
        inodes, applicable_sorting = [], []
        for inode_model in InodeModel.all_models:
            queryset = inode_model.objects.select_related('owner') \
                .filter(**lookup) \
                .annotate(owner_name=F('owner__username')) \
                .annotate(is_folder=Value(inode_model.is_folder, output_field=BooleanField()))
            if applicable_sorting := self.sorting_map.get(sorting):
                if issubclass(inode_model, applicable_sorting[0]):
                    queryset = queryset.order_by(applicable_sorting[1])
            data_fields = inode_model.data_fields + self.extra_data_fields
            inodes.extend(values | computed for values, computed in zip(
                queryset.values(*data_fields),
                ({
                    'change_url': reverse(
                        'admin:finder_inodemodel_change',
                        args=(obj.id,),
                        current_app=self.admin_site.name,
                    ),
                    'download_url': obj.get_download_url(),
                    'thumbnail_url': obj.get_thumbnail_url(),
                    'summary': obj.summary,
                } for obj in queryset))
            )
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
        folders = PinnedFolder.objects.filter(
            owner=request.user,
            folder__site=self.admin_site.name,
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
        root_folder = FolderModel.objects.get_root_folder(self.admin_site.name)
        trash_folder = FolderModel.objects.get_trash_folder(self.admin_site.name, owner=request.user)
        for folder in folders:
            if folder['id'] == current_folder.id:
                if len(folders) == 0:
                    folders.append(self.serialize_inode(fallback_folder))
                break
        else:
            if current_folder.id == trash_folder.id:
                if fallback_folder.parent_id == trash_folder.id:
                    folders.insert(0, self.serialize_inode(root_folder))
                elif fallback_folder.id != root_folder.id or len(folders) == 0:
                    folders.insert(0, self.serialize_inode(fallback_folder))
            elif current_folder.id == root_folder.id:
                folders.insert(0, self.serialize_inode(current_folder))
            else:
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
        )
        context['finder_settings'] = self.get_settings(request, obj)
        return TemplateResponse(
            request,
            self.form_template,
            context,
        )

    def get_settings(self, request, inode):
        favorite_folders = self.get_favorite_folders(request, inode.folder)
        settings = {
            'name': inode.name,
            'folder_id': inode.folder.id,
            'favorite_folders': favorite_folders,
            'csrf_token': get_token(request),
        }
        if inode.is_folder:
            trash_folder = FolderModel.objects.get_trash_folder(self.admin_site.name, owner=request.user)
            if inode.id != trash_folder.id:
                if inode.parent_id:
                    parent_url = reverse(
                        'admin:finder_inodemodel_change',
                        args=(inode.parent_id,),
                        current_app=self.admin_site.name,
                    )
                else:
                    parent_url = None
                settings.update(
                    is_root=inode.is_root,
                    is_trash=False,
                    parent_id=inode.parent_id,
                    parent_url=parent_url,
                )
                if not next(filter(lambda f: f['id'] == inode.id and f.get('is_pinned'), favorite_folders), None):
                    request.session['finder_last_folder_id'] = str(inode.id)
            else:
                settings.update(
                    is_root=False,
                    is_trash=True,
                )
        return settings
