from django.template.loaders.base import Loader as BaseLoader
from django.template.base import TemplateDoesNotExist


class Mock():
    pass


class MockLoader(BaseLoader):

    is_usable = True

    def load_template_source(self, template_name, template_dirs=None):
        if template_name == 'cms_mock_template.html':
            return '<div></div>', 'template.html'
        elif template_name == '404.html':
            return "404 Not Found", "404.html"
        else:
            raise TemplateDoesNotExist()
