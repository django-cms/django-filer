import json
from functools import lru_cache

from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.db import transaction
from django.db.models.expressions import F, Value
from django.db.models.fields import BooleanField
from django.http.response import (
    HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed, HttpResponseNotFound, HttpResponseForbidden,
    HttpResponseRedirect, JsonResponse,
)
from django.middleware.csrf import get_token
from django.template.response import TemplateResponse
from django.urls import path, reverse_lazy
from django.utils.translation import gettext

from finder.lookups import annotate_unified_queryset, lookup_by_label, sort_by_attribute
from finder.models.folder import FolderModel, PinnedFolder
from finder.models.permission import AccessControlEntry, DefaultAccessControlEntry, Privilege


class InodeAdmin(admin.ModelAdmin):
    extra_data_fields = ['owner_name', 'is_folder', 'parent']

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self.base_url = reverse_lazy('admin:finder_foldermodel_changelist', current_app=admin_site.name)

    def has_module_perms(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return obj and obj.has_permission(request.user, Privilege.WRITE)

    def has_view_permission(self, request, obj=None):
        return obj and obj.has_permission(request.user, Privilege.READ)

    def get_urls(self):
        urls = [
            path(
                'principals',
                self.admin_site.admin_view(self.lookup_principals),
            ),
            path(
                '<uuid:inode_id>/permissions',
                self.admin_site.admin_view(self.dispatch_permissions),
            ),
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
        if request.method != 'POST':
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

    def lookup_principals(self, request):
        if request.method != 'GET':
            return HttpResponseNotAllowed(f"Method {request.method} not allowed. Only GET requests are allowed.")
        lookup = request.GET.get('q', '')
        results = [{'type': 'everyone', 'principal': None, 'name': gettext("Everyone"), 'is_current_user': False}]
        for obj in get_user_model().objects.filter(username__icontains=lookup)[:10]:
            results.append({
                'type': 'user',
                'principal': obj.id,
                'name': str(obj),
                'is_current_user': obj.id == request.user.id,
            })
        for obj in Group.objects.filter(name__icontains=lookup)[:10]:
            results.append({
                'type': 'group',
                'principal': obj.id,
                'name': str(obj),
                'is_current_user': False,
            })
        return JsonResponse({'access_control_results': results})

    def dispatch_permissions(self, request, inode_id):
        def set_permissions_recursive(folder, access_control_list):
            for entry in folder.listdir():
                inode = FolderModel.objects.get_inode(id=entry['id'])
                if inode.has_permission(request.user, Privilege.ADMIN):
                    inode.update_access_control_list(access_control_list)
                if inode.is_folder:
                    set_permissions_recursive(inode, access_control_list)

        try:
            current_inode = self.get_object(request, inode_id)
        except ObjectDoesNotExist:
            return HttpResponseNotFound(f"InodeModel<{inode_id}> not found.")
        if request.method == 'GET':
            to_default = 'default' in request.GET
            return self.get_permissions(current_inode, request.user, to_default)
        if request.method == 'POST':
            try:
                if not current_inode.has_permission(request.user, Privilege.ADMIN):
                    raise PermissionDenied("Missing permissions to change access control list.")
                body = json.loads(request.body)
                access_control_list = body['access_control_list']
                to_default = body.get('to_default', False)
                recursive = body.get('recursive')
                with transaction.atomic():
                    if to_default:
                        assert current_inode.is_folder, "Default permission setting is only allowed on folders."
                        if recursive:
                            for subfolder in current_inode.descendants:
                                if subfolder.has_permission(request.user, Privilege.ADMIN):
                                    subfolder.update_default_access_control_list(access_control_list)
                        else:
                            current_inode.update_default_access_control_list(access_control_list)
                    else:
                        if recursive:
                            assert current_inode.is_folder, "Recursive permission setting is only allowed on folders."
                            set_permissions_recursive(current_inode, access_control_list)
                        current_inode.update_access_control_list(access_control_list)
            except PermissionError as exc:
                return HttpResponseForbidden(str(exc))
            except (KeyError, json.JSONDecodeError):
                return HttpResponse("Invalid JSON payload.", status=400)
            else:
                return self.get_permissions(current_inode, request.user, to_default)
        return HttpResponseNotAllowed(f"Method {request.method} not allowed. Only GET and POST requests are allowed.")

    def get_permissions(self, current_inode, current_user, to_default):
        access_control_list = []
        if to_default:
            acl_qs = DefaultAccessControlEntry.objects.filter(folder=current_inode)
        else:
            acl_qs = AccessControlEntry.objects.filter(inode=current_inode.id)
        for ace in acl_qs:
            entry = ace.as_dict
            entry['is_current_user'] = entry['type'] == 'user' and entry['principal'] == current_user.id
            access_control_list.append(entry)
        return JsonResponse({
            'access_control_list': access_control_list,
        })

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
        change_url = self.get_inode_url(ambit.slug, str(inode.id))
        data = {field: inode.serializable_value(field) for field in inode.data_fields}
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
        Return a serialized list of files and folder for the given folder.
        """
        lookup = dict(lookup_by_label(request), user=request.user, has_read_permission=True, **lookup)
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
        if request.user.is_superuser:
            can_change = Value(True, output_field=BooleanField())
            can_view = Value(True, output_field=BooleanField())
        else:
            can_change = AccessControlEntry.objects.privilege_subquery_exists(request.user, Privilege.WRITE)
            can_view = AccessControlEntry.objects.privilege_subquery_exists(request.user, Privilege.READ)
        folders = PinnedFolder.objects.values(
            'folder__id',
            'folder__name',
        ).annotate(
            id=F('folder__id'),
            name=F('folder__name'),
            is_pinned=Value(True, output_field=BooleanField()),
            can_change=can_change,
            can_view=can_view,
        ).filter(
            ambit=ambit,
            owner=request.user,
            can_view=True,
        ).values('id', 'name', 'is_pinned', 'can_change')
        folders = [dict(
            **values,
            change_url=self.get_inode_url(ambit.slug, str(values['id'])),
        ) for values in folders]
        root_folder = ambit.root_folder
        trash_folder = self.get_trash_folder(request)
        for folder in folders:
            if folder['id'] == current_folder.id:
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
        parent_url = self.get_inode_url(request._ambit.slug, str(inode.parent_id)) if inode.parent_id else None
        return {
            'name': inode.name,
            'is_folder': inode.is_folder,
            'folder_id': inode.folder.id,
            'favorite_folders': favorite_folders,
            'csrf_token': get_token(request),
            'parent_id': inode.parent_id,
            'parent_url': parent_url,
            'is_admin': inode.has_permission(request.user, Privilege.ADMIN),
            'can_change': inode.has_permission(request.user, Privilege.WRITE),
        }

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
            entry['change_url'] = self.get_inode_url(ambit.slug, str(entry['id']))

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
