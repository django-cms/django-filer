# -*- coding: utf-8 -*-
'''
Created on May 31, 2016

@author: jakob
'''

from django.core.management.base import BaseCommand
from filer.models.imagemodels import Image


class Command(BaseCommand):

    def handle(self, *args, **options):
        pks = Image.objects.all().values_list('id', flat=True)
        total = len(pks)
        for idx, pk in enumerate(pks):
            image = None
            try:
                image = Image.objects.get(pk=pk)
                self.stdout.write(u'Processing image {0} / {1} {2}'.format(idx + 1, total, image))
                self.stdout.flush()
                image.thumbnails
                image.icons
            except IOError as e:
                self.stderr.write('Failed to generate thumbnails: {0}'.format(str(e)))
                self.stderr.flush()
            finally:
                del image
