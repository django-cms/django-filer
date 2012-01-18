from django.contrib import admin
from filer.models import *
from filer.admin.folderadmin import FolderAdmin
from filer.admin.fileadmin import FileAdmin
from filer.admin.clipboardadmin import ClipboardAdmin
from filer.admin.imageadmin import ImageAdmin

from django.utils.translation import ugettext_lazy as _

# in order to generate proper localization messages
_("filer")

admin.site.register([FolderPermission,])
#admin.site.register([Folder,])
admin.site.register(Folder,FolderAdmin)
#admin.site.register([File,])
admin.site.register(File,FileAdmin)
admin.site.register(Clipboard, ClipboardAdmin)
admin.site.register(Image, ImageAdmin)