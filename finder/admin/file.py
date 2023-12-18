from django.contrib import admin
from django.forms.widgets import Media
from django.templatetags.static import static
from django.utils.html import format_html

from finder.models.file import FileModel
from .inode import InodeAdmin


@admin.register(FileModel)
class FileAdmin(InodeAdmin):
    form_template = 'admin/finder/change_file_form.html'

    @property
    def media(self):
        return Media(
            css={'all': ['admin/finder/css/finder-admin.css', 'admin/css/forms.css']},
            js=[format_html(
                '<script type="module" src="{}"></script>', static('admin/finder/js/file-admin.js')
            )],
        )

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
            download_url=inode.get_download_url(),
        )
        return settings
