#-*- coding: utf-8 -*-
from filer.fields.file import AdminFileWidget, AdminFileFormField, \
    FilerFileField
from filer.models import Video


class AdminVideoWidget(AdminFileWidget):
    pass


class AdminVideoFormField(AdminFileFormField):
    widget = AdminVideoWidget


class FilerVideoField(FilerFileField):
    default_form_class = AdminVideoFormField
    default_model_class = Video