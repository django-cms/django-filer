from django.views.generic.edit import UpdateView

from .models import TestAppModel1


class TestAppView(UpdateView):
    model = TestAppModel1
    fields = '__all__'
    template_name = 'demoapp.html'

    def get_object(self, queryset=None):
        if obj := TestAppModel1.objects.first():
            return obj
        return TestAppModel1.objects.create()

    def get_success_url(self):
        return self.request.path
