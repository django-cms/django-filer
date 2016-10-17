# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals

from django.http import Http404
from django.shortcuts import get_object_or_404, redirect

from .models import File


def canonical(request, uploaded_at, file_id):
    """
    Redirect to the current url of a public file
    """
    filer_file = get_object_or_404(File, pk=file_id, is_public=True)
    if (not filer_file.file or int(uploaded_at) != filer_file.canonical_time):
        raise Http404('No %s matches the given query.' % File._meta.object_name)
    return redirect(filer_file.url)
