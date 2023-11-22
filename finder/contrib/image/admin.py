from django.contrib import admin

from finder.admin.file import FileAdmin
from finder.contrib.image.models import ImageModel


@admin.register(ImageModel)
class ImageAdmin(FileAdmin):
    pass
