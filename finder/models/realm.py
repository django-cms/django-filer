from django.contrib.sites.models import Site
from django.db import models
from django.utils.translation import gettext_lazy as _


class RealmModel(models.Model):
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

    class Meta:
        ordering = ['site', 'slug']
        constraints = [models.UniqueConstraint(fields=['site', 'slug'], name='unique_site')]

    def __str__(self):
        return f"{self.slug} @ {self.site.name}"
