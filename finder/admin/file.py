from django.contrib import admin
from django.forms.widgets import Media
from django.http.response import HttpResponse, HttpResponseBadRequest, HttpResponseNotFound
from django.templatetags.static import static
from django.urls import path, reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from finder.models.file import FileModel
from .inode import InodeAdmin


@admin.register(FileModel)
class FileAdmin(InodeAdmin):
    form_template = 'admin/finder/change_file_form.html'
    readonly_fields = ['details', 'owner', 'created_at', 'last_modified_at', 'mime_type', 'sha1']
    exclude = ['meta_data']

    @property
    def media(self):
        return Media(
            css={'all': ['admin/finder/css/finder-admin.css', 'admin/css/forms.css']},
            js=[format_html(
                '<script type="module" src="{}"></script>', static('admin/finder/js/file-admin.js')
            )],
        )

    def get_urls(self):
        urls = [
            path(
                '<uuid:file_id>/upload',
                self.admin_site.admin_view(self.replace_file),
            ),
        ]
        urls.extend(super().get_urls())
        return urls

    @admin.display(description=_("Details"))
    def details(self, obj):
        return obj.summary

    def get_model_perms(self, *args, **kwargs):
        """Prevent showing up in the admin index."""
        return {}

    def get_ancestors(self, request, obj):
        return super().get_ancestors(request, obj.folder)

    def get_breadcrumbs(self, obj):
        breadcrumbs = super().get_breadcrumbs(obj)
        breadcrumbs.append({
            'link': None,
            'name': str(obj),
        })
        return breadcrumbs

    def replace_file(self, request, file_id):
        if request.method != 'POST':
            return HttpResponseBadRequest(f"Method {request.method} not allowed. Only POST requests are allowed.")
        if not (file_obj := self.get_object(request, file_id)):
            return HttpResponseNotFound(f"File {file_id} not found.")
        if request.content_type != 'multipart/form-data' or 'upload_file' not in request.FILES:
            return HttpResponseBadRequest(f"Content-Type {request.content_type} invalid for file upload.")
        uploaded_file = request.FILES['upload_file']
        if uploaded_file.content_type != file_obj.mime_type:
            return HttpResponseBadRequest(f"Can not replace file {file_obj.name} with different mime type.")
        # the payload of the file_obj is not replaced and remains orphaned, it may be deleted
        file_obj.file_name = file_obj.generate_filename(uploaded_file.name)
        file_obj.file_size = uploaded_file.size
        file_obj.receive_file(uploaded_file)
        file_obj.save()
        return HttpResponse(f"Replaced content of {file_obj.name} successfully.")

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        has_editable_inline_admin_formsets = False
        for inline in context['inline_admin_formsets']:
            if inline.has_add_permission or inline.has_change_permission or inline.has_delete_permission:
                has_editable_inline_admin_formsets = True
                break
        context.update(
            add=add,
            change=change,
            has_view_permission=self.has_view_permission(request, obj),
            has_add_permission=self.has_add_permission(request),
            has_change_permission=self.has_change_permission(request, obj),
            has_delete_permission=self.has_delete_permission(request, obj),
            has_editable_inline_admin_formsets=has_editable_inline_admin_formsets,
            opts=self.opts,
            save_as=self.save_as,
            show_save_and_add_another=False,
        )
        return super().render_change_form(request, context, add, change, form_url, obj)

    def get_settings(self, request, inode):
        settings = super().get_settings(request, inode)
        settings.update(
            base_url=reverse('admin:finder_filemodel_changelist', current_app=self.admin_site.name),
            download_url=inode.get_download_url(),
            thumbnail_url=inode.get_thumbnail_url(),
            filename=inode.file_name,
            file_id=inode.id,
            file_mime_type=inode.mime_type,
            editor_component=inode.editor_component,
        )
        return settings
