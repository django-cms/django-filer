from django.contrib.auth import get_user_model
from django.utils.deprecation import MiddlewareMixin


class AutoLoginMiddleware(MiddlewareMixin):
    """
    Middleware to automatically login as admin user.
    """

    def process_request(self, request):
        admin_user = get_user_model().objects.first()
        if not admin_user:
            admin_user = get_user_model().objects.create_user(
                username='admin',
                password='secret',
                is_superuser=True,
                is_staff=True,
            )
        request.user = admin_user
