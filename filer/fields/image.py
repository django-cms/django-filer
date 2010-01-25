from django.utils.translation import ugettext as _
from django.utils.text import truncate_words
from django.utils import simplejson
from django.db import models
from django import forms
from django.contrib.admin.widgets import ForeignKeyRawIdWidget
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from sorl.thumbnail.base import ThumbnailException
from filer.settings import FILER_STATICMEDIA_PREFIX
from django.conf import settings as globalsettings
from filer.fields.file import AdminFileWidget, AdminFileFormField, FilerFileField
from filer.models import Image

class AdminImageWidget(AdminFileWidget):
    pass

class AdminImageFormField(AdminFileFormField):
    widget = AdminImageWidget

class FilerImageField(FilerFileField):
    default_form_class = AdminImageFormField
    default_model_class = Image