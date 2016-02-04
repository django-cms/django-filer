# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from filer.fields.file import FilerFileField
from filer.fields.image import FilerImageField
from filer.validators import validate_documents, validate_html5_images


class Example(models.Model):
    title = models.CharField(
        verbose_name='title',
        max_length=100,)
    illustration_browse_only = FilerImageField(
        verbose_name='illustration',
        default_direct_upload_enabled=True,  # add a "browse" button with ajax upload
        default_file_lookup_enabled=False,  # remove the "choose" link
        default_folder_key='IMAGES',
        null=True, blank=True,
        related_name='illustrations+',)
    file_choose_only = FilerFileField(
        verbose_name='file',
        default_direct_upload_enabled=False,  # remove the "browse" button with ajax upload
        default_file_lookup_enabled=True,  # add a "choose" link
        default_folder_key='USER_OWN_FOLDER',
        null=True, blank=True,
        related_name='files+',)
    document_choose_or_browse = FilerFileField(
        verbose_name='document',
        help_text='CSV, PDF, ODT, DOC...',
        default_direct_upload_enabled=True,  # add a "browse" button with ajax upload
        default_file_lookup_enabled=True,  # add a "choose" link
        default_folder_key='DOCUMENTS',
        validators=[validate_documents, ],
        null=True, blank=True,
        related_name='documents+',)

    class Meta:
        app_label = 'thirdparty_app'
        verbose_name = 'example'
        verbose_name_plural = 'examples'

    def __str__(self):
        return '%s' % self.title


class ExampleGalleryElement(models.Model):
    order = models.PositiveIntegerField(
        verbose_name='order',
        blank=True, null=False,
        default=0,
    )
    image = FilerImageField(
        verbose_name='image',
        default_direct_upload_enabled=True,  # add a "browse" button with ajax upload
        default_file_lookup_enabled=False,  # remove the "choose" link
        default_folder_key='IMAGES',
        null=True, blank=True,
        validators=[validate_html5_images, ],
        related_name='images+',)
    example = models.ForeignKey(Example,
        verbose_name='example',
        related_name='gallery_elements',)

    class Meta:
        app_label = 'thirdparty_app'
        ordering = ('example__pk', 'order',)
        verbose_name = 'gallery'
        verbose_name_plural = 'galleries'
