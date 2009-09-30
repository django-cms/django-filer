from filer.models.foldermodels import *
from filer.models.filemodels import * 
from filer.models.imagemodels import *
from filer.models.clipboardmodels import *
from filer.models.virtualitems import *



from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
if not 'filer.context_processors.media' in settings.TEMPLATE_CONTEXT_PROCESSORS: raise ImproperlyConfigured("filer needs 'filer.context_processors.media' to be in settings.TEMPLATE_CONTEXT_PROCESSORS")
