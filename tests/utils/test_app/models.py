from django.db import models

from filer.fields.file import FilerFileField
from filer.fields.folder import FilerFolderField
from filer.fields.image import FilerImageField


class MyModel(models.Model):

    general = FilerFileField(related_name='test_file', on_delete=models.CASCADE)
    image = FilerImageField(related_name='test_image', on_delete=models.CASCADE)
    folder = FilerFolderField(related_name='test_folder', on_delete=models.CASCADE)
