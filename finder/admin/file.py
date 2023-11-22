from django.contrib import admin
from django.forms.widgets import Media

from finder.models.file import FileModel
from .inode import InodeAdmin


@admin.register(FileModel)
class FileAdmin(InodeAdmin):
    fields = ['name']

    @property
    def media(self):
        return Media(
            css={'all': ['admin/finder/css/finder-admin.css']},
            js=['admin/finder/js/file-admin.js'],
        )

    def get_model_perms(self, *args, **kwargs):
        """Prevent showing up in the admin index."""
        return {}

    def get_ancestors(self, request, obj):
        return super().get_ancestors(request, obj.folder)

    def get_breadcrumbs(self, request, obj):
        breadcrumbs = super().get_breadcrumbs(request, obj)
        breadcrumbs.append({
            'link': None,
            'name': str(obj),
        })
        return breadcrumbs
