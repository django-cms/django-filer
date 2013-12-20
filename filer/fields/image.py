#-*- coding: utf-8 -*-
from filer.fields.file import AdminFileWidget, AdminFileFormField, FilerFileField


class AdminImageWidget(AdminFileWidget):
    pass


class AdminImageFormField(AdminFileFormField):
    widget = AdminImageWidget


class FilerImageField(FilerFileField):
    def get_default_form_class(self):
        return AdminImageFormField

    def get_default_model_class(self):
        from filer.models import Image
        return Image
