#-*- coding: utf-8 -*-
from filer.settings import FILER_ADMIN_ICON_SIZES, FILER_STATICMEDIA_PREFIX
from django.db import models
from django.utils.translation import ugettext_lazy as _
from datetime import datetime


class IconsMixin(object):
    """
    Can be used on any model that has a _icon attribute. will return a dict
    containing urls for icons of different sizes with that name.
    """
    @property
    def icons(self):
        r = {}
        if getattr(self, '_icon', False):
            for size in FILER_ADMIN_ICON_SIZES:
                r[size] = "%sicons/%s_%sx%s.png" % (
                            FILER_STATICMEDIA_PREFIX, self._icon, size, size)
        return r


class TrashableMixin(models.Model):
    """
        Abstract model that makes a regular django model restorable.
        This mixin needs to be placed first in the list of inherited classes
            in order to overwrite the delete method as it should.
    """

    deleted_at = models.DateTimeField(
        _('deleted at'), editable=False, blank=True, null=True)

    class Meta:
        abstract = True

    def soft_delete(self):
        raise NotImplementedError

    def hard_delete(self):
        raise NotImplementedError

    def delete_restorable(self, *args, **kwargs):
        to_trash = kwargs.get('to_trash', True)
        if not self.deleted_at and to_trash:
            self.soft_delete()
        else:
            self.hard_delete()

    def restore(self, commit=True):
        self.deleted_at = None
        if commit:
            self.save()


class TrashableQuerysetMixin(object):

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def trash(self):
        return self.filter(deleted_at__isnull=False)

