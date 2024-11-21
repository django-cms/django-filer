import json

from django.contrib import admin
from django.contrib.sites.shortcuts import get_current_site
from django.db.models.expressions import F, Value
from django.db.models.fields import BooleanField
from django.http.response import HttpResponseBadRequest, HttpResponseNotFound, HttpResponseRedirect, JsonResponse
from django.middleware.csrf import get_token
from django.template.response import TemplateResponse
from django.urls import path, reverse

from finder.lookups import annotate_unified_queryset, lookup_by_label, sort_by_attribute
from finder.models.folder import FolderModel, PinnedFolder
from finder.models.realm import RealmModel


class InodeAdmin(admin.ModelAdmin):
    extra_data_fields = ['owner_name', 'is_folder', 'parent']

    def get_urls(self):
        urls = [
            path(
                '<uuid:folder_id>/toggle_pin',
                self.admin_site.admin_view(self.toggle_pin),
            ),
        ]
        urls.extend(super().get_urls())
        return urls

    def get_object(self, request, inode_id, *args):
        site = get_current_site(request)
        return FolderModel.objects.get_inode(id=inode_id)

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
        realm = self.get_realm(request)
        pinned_folder, created = PinnedFolder.objects.get_or_create(
            realm=realm,
            owner=request.user,
            folder_id=pinned_id,
        )
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
        try:
            realm = RealmModel.objects.get(site=get_current_site(request), slug=self.admin_site.name)
        except RealmModel.DoesNotExist:
            root_folder = FolderModel.objects.create(owner=request.user, name='__root__')
            realm = RealmModel.objects.create(
                site=get_current_site(request),
                slug=self.admin_site.name,
                root_folder=root_folder,
            )
        return realm

    def get_root_folder(self, request):
        realm = self.get_realm(request)
        return FolderModel.objects.get_root_folder(realm)

    def get_trash_folder(self, request):
        realm = self.get_realm(request)
        return FolderModel.objects.get_trash_folder(realm, request.user)

    def get_fallback_folder(self, request):
        try:
            last_folder_id = request.session['finder_last_folder_id']
            return FolderModel.objects.get(id=last_folder_id)
        except (FolderModel.DoesNotExist, KeyError):
            return self.get_root_folder(request)

    def get_inodes(self, request, **lookup):
        """
        Return a serialized list of file/folder-s for the given folder.
        """
        lookup = dict(lookup_by_label(request), **lookup)
        unified_queryset = FolderModel.objects.filter_unified(**lookup)
        unified_queryset = sort_by_attribute(request, unified_queryset)
        self.annotate_unified_queryset(unified_queryset)
        return unified_queryset

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
        site = get_current_site(request)
        folders = PinnedFolder.objects.filter(
            realm__site=site,
            realm__slug=self.admin_site.name,
            owner=request.user,
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
        raise NotImplementedError()
        return {}

    def get_menu_extension_settings(self, request):
        """
        Hook to return the React context for extending menu items specific to this model.
        """
        return {}

    def annotate_unified_queryset(self, queryset):
        annotate_unified_queryset(queryset)
        for entry in queryset:
            entry.update(
                change_url=reverse(
                    'admin:finder_inodemodel_change',
                    args=(entry['id'],),
                    current_app=self.admin_site.name,
                )
            )
