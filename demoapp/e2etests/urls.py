"""
URLs used by the end-to-end tests.

Django forces ``DEBUG = False`` while tests run, so ``static()`` in
``demoapp.urls`` never contributes the media route. The browser however does
need to load thumbnails, hence media files are served unconditionally here.
"""

from django.conf import settings
from django.http import HttpResponse
from django.urls import path, re_path, reverse
from django.views.static import serve

from demoapp.urls import urlpatterns as demoapp_urlpatterns


def cms_modal(request):
    """
    Mimic django CMS, which edits plugins in an iframe inside its modal. Like django CMS, the page
    closes its modal on Escape; the test checks `window.cmsModalClosed`. With `?modal=0` the
    iframe is not inside a modal.
    """
    modal_class = 'cms-modal' if request.GET.get('modal') != '0' else 'other-container'
    return HttpResponse(f"""<!DOCTYPE html>
<html><body>
<div class="{modal_class}"><div class="cms-modal-frame">
<iframe src="{reverse('demoapp')}" style="width: 600px; height: 400px;"></iframe>
</div></div>
<script>
window.cmsModalClosed = false;
document.addEventListener('keydown', event => {{ if (event.key === 'Escape') window.cmsModalClosed = true; }});
</script>
</body></html>""")


urlpatterns = demoapp_urlpatterns + [
    path('cms-modal/', cms_modal, name='cms-modal'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]
