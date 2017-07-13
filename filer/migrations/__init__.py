# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals


def new_file_is_published_status():
    from filer import settings
    return settings.FILER_PUBLISHER_NEW_FILE_IS_PUBLISHED_STATUS
