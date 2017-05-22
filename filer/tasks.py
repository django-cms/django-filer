# -*- coding: utf-8 -*-
from celery.app import shared_task

from easy_thumbnails.files import generate_all_aliases


@shared_task
def generate_thumbnails(model, pk, field):
    from filer.utils.filer_easy_thumbnails import load_aliases
    load_aliases()
    instance = model._default_manager.get(pk=pk)
    fieldfile = getattr(instance, field)
    generate_all_aliases(fieldfile, include_global=True)
