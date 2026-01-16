import logging

from django.contrib.sites.models import Site
from django.core.files.storage import storages
from django.db import models
from django.utils.functional import cached_property


logger = logging.getLogger(__name__)


class AmbitModel(models.Model):
    """
    The AmbitModel is the top-level container for each folder tree.
    Each AmbitModel has one root folder and a trash folder per user.
    """
    slug = models.SlugField(
        unique=True,
    )
    verbose_name = models.CharField(
        max_length=200,
    )
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        null=True,
    )
    admin_name = models.CharField(
        max_length=100,
        null=True,
    )
    root_folder = models.OneToOneField(
        'FolderModel',
        on_delete=models.CASCADE,
        related_name='ambit',
        editable=False,
    )
    trash_folders = models.ManyToManyField(
        'FolderModel',
        related_name='+',
        editable=False,
    )
    _original_storage = models.CharField(
        default='finder_public',
    )
    _sample_storage = models.CharField(
        default='finder_public_samples',
    )

    def __str__(self):
        return self.slug

    @cached_property
    def original_storage(self):
        return storages[self._original_storage]

    @cached_property
    def sample_storage(self):
        return storages[self._sample_storage]
