from django.views.generic.edit import UpdateView

from testapp.models import TestAppModel


class TestAppView(UpdateView):
    model = TestAppModel
    fields = '__all__'
    template_name = 'testapp.html'

    def get_object(self, queryset=None):
        if obj := TestAppModel.objects.first():
            return obj
        return TestAppModel.objects.create()

    def get_success_url(self):
        return self.request.path

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
