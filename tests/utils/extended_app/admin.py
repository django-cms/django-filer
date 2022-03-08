from django.contrib import admin

from filer.admin import FileAdmin, ImageAdmin

from .models import ExtImage, Video


admin.site.register(Video, FileAdmin)
admin.site.register(ExtImage, ImageAdmin)
