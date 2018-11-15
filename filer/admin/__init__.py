# -*- coding: utf-8 -*-
from django.contrib import admin

from ..models import Clipboard, File, Folder, FolderPermission, ThumbnailOption
from ..settings import FILER_IMAGE_MODEL
from ..utils.loader import load_model
from .clipboardadmin import ClipboardAdmin
from .fileadmin import FileAdmin
from .folderadmin import FolderAdmin
from .imageadmin import ImageAdmin
from .permissionadmin import PermissionAdmin
from .thumbnailoptionadmin import ThumbnailOptionAdmin

Image = load_model(FILER_IMAGE_MODEL)


admin.site.register(Folder, FolderAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(Clipboard, ClipboardAdmin)
admin.site.register(Image, ImageAdmin)
admin.site.register(FolderPermission, PermissionAdmin)
admin.site.register(ThumbnailOption, ThumbnailOptionAdmin)
