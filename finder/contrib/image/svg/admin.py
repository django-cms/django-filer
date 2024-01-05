from django.contrib import admin

from finder.contrib.image.admin import ImageAdmin
from finder.contrib.image.svg.models import SVGImageModel


admin.site.register(SVGImageModel, ImageAdmin)
