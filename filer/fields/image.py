# -*- coding: utf-8 -*-
from __future__ import absolute_import

from ..models import Image
from .file import AdminFileFormField, AdminFileWidget, FilerFileField


class AdminImageWidget(AdminFileWidget):
    pass


class AdminImageFormField(AdminFileFormField):
    widget = AdminImageWidget


class FilerImageField(FilerFileField):
    default_form_class = AdminImageFormField
    default_model_class = Image
