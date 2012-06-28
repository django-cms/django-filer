#-*- coding: utf-8 -*-
from django.contrib import admin
from filer import settings
from filer.admin.clipboardadmin import ClipboardAdmin
from filer.admin.fileadmin import FileAdmin
from filer.admin.folderadmin import FolderAdmin
from filer.admin.imageadmin import ImageAdmin
from filer.admin.permissionadmin import PermissionAdmin
from filer.models import Folder, File, Clipboard, Image
from filer.models.permissionmodels import Permission

if settings.FILER_ENABLE_PERMISSIONS:
    admin.site.register(Permission, PermissionAdmin)
admin.site.register(Folder, FolderAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(Clipboard, ClipboardAdmin)
admin.site.register(Image, ImageAdmin)
