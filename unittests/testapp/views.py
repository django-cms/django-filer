from django.views.generic.edit import UpdateView

from .models import SampleAppModel1


class TestAppView(UpdateView):
    model = SampleAppModel1
    fields = '__all__'
    template_name = 'demoapp.html'

    def get_object(self, queryset=None):
        if obj := SampleAppModel1.objects.first():
            return obj
        return SampleAppModel1.objects.create()

    def get_success_url(self):
        return self.request.path
