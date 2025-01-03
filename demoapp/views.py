from django.views.generic.edit import UpdateView

from demoapp.models import DemoAppModel


class DemoAppView(UpdateView):
    model = DemoAppModel
    fields = '__all__'
    template_name = 'demoapp.html'

    def get_object(self, queryset=None):
        if obj := DemoAppModel.objects.first():
            return obj
        return DemoAppModel.objects.create()

    def get_success_url(self):
        return self.request.path

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
