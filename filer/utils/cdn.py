import datetime
import urlparse

from django.utils import timezone

from filer import settings as filer_settings


def get_cdn_url(file_obj, url):
    """If the CDN version of the file is up to date, return it from there"""
    cdn_domain = getattr(filer_settings, 'CDN_DOMAIN', None)
    if cdn_domain is None:
        return url

    invalidated_at = file_obj.modified_at + datetime.timedelta(
        seconds=filer_settings.CDN_INVALIDATION_TIME)
    # django uses django.utils.timezone.now() to set value for
    #   modified_at field;
    # it makes sense to use the same method to fetch current time;
    now = timezone.now()
    if timezone.is_naive(invalidated_at):
        tz_used = timezone.get_default_timezone()
        invalidated_at = timezone.make_aware(invalidated_at, tz_used)
    else:
        tz_used = invalidated_at.tzinfo
    # since current time might have a timezone aware datetime(depending on
    #   django settings), make sure it will be converted to the same
    #   timezone as invalidated_at
    if timezone.is_naive(now):
        now = timezone.make_aware(now, tz_used)
    else:
        now = now.astimezone(tz_used)

    if invalidated_at < now:
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
        return urlparse.urlunparse(
            (scheme, cdn_domain, path, params, query, fragment))
    else:
        return url
