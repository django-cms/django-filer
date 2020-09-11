from django.contrib import admin


class ThumbnailOptionAdmin(admin.ModelAdmin):
    list_display = ('name', 'width', 'height')
