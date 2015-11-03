#-*- coding: utf-8 -*-
from filer.fields.file import AdminFileWidget, AdminFileFormField, \
    FilerFileField
from filer.models import Image


class AdminImageWidget(AdminFileWidget):

    def get_custom_preview_image(self, obj):
        return obj.url if obj else None


class AdminImageFormField(AdminFileFormField):
    widget = AdminImageWidget


class FilerImageField(FilerFileField):
    default_form_class = AdminImageFormField
    default_model_class = Image
