from django import forms
from django.contrib import admin
from filer.admin.fileadmin import FileAdmin
from filer.models import Archive
from django.conf.urls.defaults import patterns, url
from django.http import HttpResponseRedirect
from zipfile import ZipFile


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
    
    def get_urls(self):
        urls = super(ArchiveAdmin, self).get_urls()
        archive_urls = patterns('',
            url(r'^(?P<file_id>\d+)/extract/$', self.admin_site.admin_view(self.extract),
                name='filer_file_extract'),
        )
        return archive_urls + urls

    def extract(self, request, file_id):
        archive = Archive.objects.get(id=file_id)
        archive.extract()
        # return HttpResponse('')
