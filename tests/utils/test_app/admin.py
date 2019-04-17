# -*- coding: utf-8 -*-
from __future__ import absolute_import

from django.contrib import admin

from .models import MyModel


class MyModelAdmin(admin.ModelAdmin):
    model = MyModel

admin.site.register(MyModel, MyModelAdmin)
