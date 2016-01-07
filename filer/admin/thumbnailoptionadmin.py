from django.contrib import admin
from filer.models import ThumbnailOption

class ThumbnailOptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'width', 'height')
