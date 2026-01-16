import json
from functools import lru_cache

from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.options import IS_POPUP_VAR
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.expressions import F, Value
from django.db.models.fields import BooleanField
from django.http.response import (
    HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed, HttpResponseNotFound, HttpResponseRedirect,
    JsonResponse,
)
from django.middleware.csrf import get_token
from django.template.response import TemplateResponse
from django.urls import path, reverse, reverse_lazy
from django.utils.translation import gettext

from finder.lookups import annotate_unified_queryset, lookup_by_label, sort_by_attribute
from finder.models.folder import FolderModel, PinnedFolder


class InodeAdmin(admin.ModelAdmin):
    extra_data_fields = ['owner_name', 'is_folder', 'parent']

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self.base_url = reverse_lazy('admin:finder_foldermodel_changelist', current_app=admin_site.name)

    def get_urls(self):
        urls = [
            path(
                '<uuid:folder_id>/toggle_pin',
                self.admin_site.admin_view(self.toggle_pin),
            ),
        ]
        urls.extend(super().get_urls())
        return urls

    @lru_cache
    def get_inode_url(self, slug, inode_id):
        parts = self.base_url.split('/')
        parts = [slug if part == 'foldermodel' else part for part in parts]
        if parts[-1] == '':
            parts[-1] = inode_id
        else:
            parts.append(inode_id)
        return '/'.join(parts)

    def get_object(self, request, inode_id, *args):
        return FolderModel.objects.get_inode(id=inode_id)

    def check_for_valid_post_request(self, request, folder_id):
        if request.method not in ['POST', 'PUT']:
            return HttpResponseNotAllowed(f"Method {request.method} not allowed. Only POST requests are allowed.")
        if request.content_type != 'application/json':
            return HttpResponse(
                f"Invalid content-type {request.content_type}. Only application/json is allowed.",
                status=415,
            )
        try:
            folder = self.get_object(request, folder_id)
            request._ambit = folder.get_ambit()
        except ObjectDoesNotExist:
            return HttpResponseNotFound(f"Folder with id “{folder_id}” not found.")

    def toggle_pin(self, request, folder_id):
        if response := self.check_for_valid_post_request(request, folder_id):
            return response
        body = json.loads(request.body)
        current_folder = self.get_object(request, folder_id)
        if not (pinned_id := body.get('pinned_id')):
            return HttpResponseBadRequest("No pinned_id provided.")
        pinned_folder, created = PinnedFolder.objects.get_or_create(
            ambit=request._ambit,
            owner=request.user,
            folder_id=pinned_id,
        )
        if created:
            request.session['finder_last_folder_id'] = None
        else:
            parent_folder = pinned_folder.folder.parent
            pinned_folder.delete()
            if str(folder_id) == pinned_id:
                success_url = self.get_inode_url(request._ambit.slug, str(parent_folder.id))
                return JsonResponse({'success_url': success_url})
        return JsonResponse({
            'favorite_folders': self.get_favorite_folders(request, current_folder),
        })

    def serialize_inode(self, ambit, inode):
        data = {field: inode.serializable_value(field) for field in inode.data_fields}
        change_url = self.get_inode_url(ambit.slug, str(inode.id))
        data.update(
            owner_name=inode.owner.username if inode.owner else None,
            is_folder=inode.is_folder,
            change_url=change_url,
            download_url=inode.get_download_url(ambit),
            thumbnail_url=inode.get_thumbnail_url(ambit),
            summary=inode.summary,
        )
        if (inode.is_folder):
            data.update(is_root=inode.is_root)
        return data

    def get_trash_folder(self, request):
        return FolderModel.objects.get_trash_folder(request._ambit, request.user)

    def get_fallback_folder(self, request):
        try:
            last_folder_id = request.session['finder_last_folder_id']
            return FolderModel.objects.get(id=last_folder_id)
        except (FolderModel.DoesNotExist, KeyError):
            return request._ambit.root_folder

    def get_inodes(self, request, **lookup):
        """
        Return a serialized list of file/folder-s for the given folder.
        """
        lookup = dict(lookup_by_label(request), **lookup)
        unified_queryset = FolderModel.objects.filter_unified(**lookup)
        unified_queryset = sort_by_attribute(request, unified_queryset)
        self.annotate_unified_queryset(request._ambit, unified_queryset)
        return unified_queryset

    def get_breadcrumbs(self, obj):
        ambit = obj.folder.get_ambit()
        breadcrumbs = [{
            'link': self.get_inode_url(ambit.slug, str(folder.id)),
            'name': str(folder),
        } for folder in obj.ancestors]
        breadcrumbs.reverse()
        return breadcrumbs

    def get_favorite_folders(self, request, current_folder):
        ambit = request._ambit
        folders = PinnedFolder.objects.filter(
            ambit=ambit,
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
            change_url=self.get_inode_url(ambit.slug, str(values['id'])),
        ) for values in folders]
        fallback_folder = self.get_fallback_folder(request)
        root_folder = ambit.root_folder
        trash_folder = self.get_trash_folder(request)
        for folder in folders:
            if folder['id'] == current_folder.id:
                if len(folders) == 0:  # TODO: is this ever possible?
                    folders.append(self.serialize_inode(ambit, fallback_folder))
                break
        else:
            if current_folder.id == root_folder.id:
                folders.insert(0, self.serialize_inode(ambit, current_folder))
            elif current_folder.id != trash_folder.id:
                folders.append(self.serialize_inode(ambit, current_folder))
        if trash_folder.num_children > 0:
            inode_data = self.serialize_inode(ambit, trash_folder)
            inode_data.update(is_trash=True)
            folders.append(inode_data)
        return folders

    def changelist_view(self, request, extra_context=None):
        return HttpResponseBadRequest(f"{request.path} must be converted to ambit.")

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
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
            settings['parent_url'] = self.get_inode_url(request._ambit.slug, str(inode.parent_id))
        else:
            settings['parent_url'] = None
        return settings

    def get_folderitem_settings(self, request, inode):
        """
        Hook to return the context for the folder item.
        """
        raise NotImplementedError()

    def get_menu_extension_settings(self, request):
        """
        Hook to return the React context for extending menu items specific to this model.
        """
        return {}

    def annotate_unified_queryset(self, ambit, queryset):
        annotate_unified_queryset(ambit, queryset)
        for entry in queryset:
            entry.update(
                change_url=self.get_inode_url(ambit.slug, str(entry['id'])),
                # change_url=reverse(
                #     'admin:finder_inodemodel_change',
                #     args=(entry['id'],),
                #     current_app=self.admin_site.name,
                # )
            )

    def response_post_save_change(self, request, obj):
        ambit = obj.folder.get_ambit()
        post_url = self.get_inode_url(ambit.slug, str(obj.folder.id))
        return HttpResponseRedirect(post_url)

    def delete_model(self, request, obj):
        request._ambit = obj.folder.get_ambit()
        request.session['finder_last_folder_id'] = str(obj.folder.id)
        obj.delete()

    def response_delete(self, request, obj_display, obj_id):
        if IS_POPUP_VAR in request.POST:
            raise NotImplementedError("Popup delete response is not implemented yet.")

        self.message_user(
            request,
            gettext("The {name} “{obj}” was deleted successfully.").format(
                name=self.opts.verbose_name,
                obj=obj_display,
            ),
            messages.SUCCESS,
        )

        post_url = self.get_inode_url(request._ambit.slug, str(request.session['finder_last_folder_id']))
        return HttpResponseRedirect(post_url)
