# -*- coding: utf-8 -*-

from django.contrib import admin
from .clipboardadmin import ClipboardAdmin
from .fileadmin import FileAdmin
from .folderadmin import FolderAdmin
from .imageadmin import ImageAdmin
from .thumbnailoptionadmin import ThumbnailOptionAdmin
from .permissionadmin import PermissionAdmin
from ..models import FolderPermission, Folder, File, Clipboard, Image, ThumbnailOption


admin.site.register(Folder, FolderAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(Clipboard, ClipboardAdmin)
admin.site.register(Image, ImageAdmin)
admin.site.register(FolderPermission, PermissionAdmin)
admin.site.register(ThumbnailOption, ThumbnailOptionAdmin)
