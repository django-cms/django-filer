# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from filer import settings as filer_settings
from filer.models import Folder
from filer.utils.loader import load_object


def get_default_folder_getter():
    path = filer_settings.FILER_DEFAULT_FOLDER_GETTER
    if path:
        if path == 'filer.utils.folders.DefaultFolderGetter':
            return DefaultFolderGetter
        return load_object(path)
    raise Exception('FILER_DEFAULT_FOLDER_GETTER improperly configured')


class DefaultFolderGetter(object):
    """
    Default Folder getter to configure some "dynamic" folders
    You just have to add a method named as the key attr. exemple :

    @classmethod
    def USER_OWN_FOLDER(cls, request):
        if not request.user.is_authenticated():
            return None
        parent_kwargs = {
            name: 'users_files',
            
        }
        return cls._get_or_create(name=user.username, owner=user, parent_kwargs=parent_kwargs)
    """

    @classmethod
    def _get_or_create(cls, name, owner=None, parent_kwargs=None):
        filters = {}
        if parent_kwargs:
            parent_folder, created = Folder.objects.get_or_create(**parent_kwargs)
            filters['parent_id'] = parent_folder.pk
        else:
            filters['parent_id__isnull'] = True
        if owner:
            filters['owner'] = owner
        folder = Folder.objects.filter(**filters)[0:1]
        if not folder:
            folder = Folder()
            folder.name = name
            if parent_kwargs:
                folder.parent_id = parent_folder.pk
            if owner:
                folder.owner = owner
            folder.save()
        else:
            folder = folder[0]
        return folder

    @classmethod
    def get(cls, key, request):
        if hasattr(cls, key):
            getter = getattr(cls, key)
            if callable(getter):
                return getter(request)
        return None
