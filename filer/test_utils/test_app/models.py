# -*- coding: utf-8 -*-
from django.db import models
from filer.fields.folder import FilerFolderField
from filer.fields.image import FilerImageField
from filer.fields.file import FilerFileField


class TestModel(models.Model):

    file = FilerFileField(related_name='test_file')
    image = FilerImageField(related_name='test_image')
    folder = FilerFolderField(related_name='test_folder')