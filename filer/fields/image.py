#-*- coding: utf-8 -*-
from filer.fields.file import AdminFileWidget, AdminFileFormField, \
    FilerFileField
from filer.models import Image


class AdminImageWidget(AdminFileWidget):
    pass


class AdminImageFormField(AdminFileFormField):
    widget = AdminImageWidget


class FilerImageField(FilerFileField):
    default_form_class = AdminImageFormField
    default_model_class = Image
