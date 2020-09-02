from django.contrib import admin

from .models import MyModel


class MyModelAdmin(admin.ModelAdmin):
    model = MyModel


admin.site.register(MyModel, MyModelAdmin)
