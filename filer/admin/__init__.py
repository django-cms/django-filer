from django.contrib import admin
from filer.models import *


admin.site.register([FolderPermission,])



admin.site.register([File,])
admin.site.register([Image,])




from filer.admin.folderadmin import FolderAdmin
#admin.site.register([Folder,])
admin.site.register(Folder,FolderAdmin)

#from filer.admin.folderadmin import FileAdmin
#admin.site.register([Folder,])
#admin.site.register(File,FileAdmin)

from filer.admin.clipboardadmin import ClipboardAdmin
admin.site.register(Clipboard, ClipboardAdmin)