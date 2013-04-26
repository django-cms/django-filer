from django import forms
from django.contrib import admin
from filer.admin.fileadmin import FileAdmin
from filer.models import Archive

class ArchiveAdminForm(forms.ModelForm):

    class Meta:
        model = Archive

    class Media:
        css = {
            # 'all': (settings.MEDIA_URL + 'filer/css/focal_point.css',)
        }
        js = (
            # filer_settings.FILER_STATICMEDIA_PREFIX + 'js/raphael.js',
            # filer_settings.FILER_STATICMEDIA_PREFIX + 'js/focal_point.js',
        )


class ArchiveAdmin(FileAdmin):
    form = ArchiveAdminForm

