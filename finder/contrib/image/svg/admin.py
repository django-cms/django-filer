from django.contrib import admin

from finder.admin.file import FileAdmin
from finder.contrib.image.svg.models import SVGImageModel


@admin.register(SVGImageModel)
class SVGImageAdmin(FileAdmin):
    pass
