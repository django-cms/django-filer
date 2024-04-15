from django.contrib import admin

from .models import MyModel


@admin.register(MyModel)
class MyModelAdmin(admin.ModelAdmin):
    model = MyModel
