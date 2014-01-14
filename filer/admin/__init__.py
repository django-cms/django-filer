#-*- coding: utf-8 -*-
from django.contrib import admin
from filer.admin.clipboardadmin import ClipboardAdmin
from filer.admin.fileadmin import FileAdmin
from filer.admin.folderadmin import FolderAdmin
from filer.admin.imageadmin import ImageAdmin
from filer.admin.archiveadmin import ArchiveAdmin
from filer.models import (Folder, File, Clipboard, Image,
                          Archive)

from filer.admin.trashadmin import Trash, TrashAdmin

admin.site.register(Folder, FolderAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(Clipboard, ClipboardAdmin)
admin.site.register(Image, ImageAdmin)
admin.site.register(Archive, ArchiveAdmin)
admin.site.register(Trash, TrashAdmin)
