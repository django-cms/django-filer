# -*- coding: utf-8 -*-

from filer.utils.folders import DefaultFolderGetter


class CustomFolderGetter(DefaultFolderGetter):

    @classmethod
    def USER_OWN_FOLDER(cls, request):
        user = request.user
        if not user.is_authenticated():
            return None
        return cls._get_or_create(name=user.username,
                                  owner=user,
                                  parent_kwargs={'name': 'users_files', 'parent': None})

    @classmethod
    def IMAGES(cls, request):
        user = request.user
        if not user.is_authenticated():
            return None
        return cls._get_or_create(name='Images')

    @classmethod
    def DOCUMENTS(cls, request):
        user = request.user
        if not user.is_authenticated():
            return None
        return cls._get_or_create(name='Documents')
