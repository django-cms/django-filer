# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.contrib import admin

from filer.test_utils.thirdparty_app.models import Example


class ExampleAdmin(admin.ModelAdmin):
    pass

admin.site.register(Example, ExampleAdmin)
