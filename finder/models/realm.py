from django.contrib.sites.models import Site
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from django.core.files.storage import storages


class RealmModelManager(models.Manager):
    def get_default(self, slug=None):
        site = Site.objects.get_current()
        if slug is None:
            slug = 'admin'
        return self.get(site=site, slug=slug)


class RealmModel(models.Model):
    """
    The RealmModel is the top-level container for each tennant. This usually is associated with a
    Django Admin Site.
    Each RealmModel has one root folder and a trash folder per user.
    """
    site = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        verbose_name=_("Site"),
    )
    slug = models.SlugField(
        _("Slug"),
        max_length=200,
        null=True,
        editable=False,
    )
    root_folder = models.OneToOneField(
        'FolderModel',
        on_delete=models.CASCADE,
        related_name='realm',
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

    class Meta:
        ordering = ['site', 'slug']
        constraints = [models.UniqueConstraint(fields=['site', 'slug'], name='unique_site')]

    objects = RealmModelManager()

    def __str__(self):
        return f"{self.slug} @ {self.site.name}"

    @cached_property
    def original_storage(self):
        return storages[self._original_storage]

    @cached_property
    def sample_storage(self):
        return storages[self._sample_storage]
