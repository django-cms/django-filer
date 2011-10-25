#-*- coding: utf-8 -*-
from django.contrib import admin
from filer import settings
from filer.admin.clipboardadmin import ClipboardAdmin
from filer.admin.fileadmin import FileAdmin
from filer.admin.folderadmin import FolderAdmin
from filer.admin.imageadmin import ImageAdmin
from filer.admin.videoadmin import VideoAdmin
from filer.admin.permissionadmin import PermissionAdmin
from filer.models import FolderPermission, Folder, File, Clipboard, Image, Video

if settings.FILER_ENABLE_PERMISSIONS:
    admin.site.register(FolderPermission, PermissionAdmin)
admin.site.register(Folder, FolderAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(Clipboard, ClipboardAdmin)
admin.site.register(Image, ImageAdmin)
admin.site.register(Video, VideoAdmin)
