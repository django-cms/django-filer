#-*- coding: utf-8 -*-
from django.contrib import admin
from filer import settings
from filer.admin.clipboardadmin import ClipboardAdmin
from filer.admin.fileadmin import FileAdmin
from filer.admin.folderadmin import FolderAdmin
from filer.admin.imageadmin import ImageAdmin
#from filer.admin.permissionadmin import PermissionAdmin
from filer.models import Folder, File, Clipboard, Image

if settings.FILER_ENABLE_PERMISSIONS:
    pass
#    admin.site.register(FolderPermission, PermissionAdmin)
admin.site.register(Folder, FolderAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(Clipboard, ClipboardAdmin)
admin.site.register(Image, ImageAdmin)
