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
    if timezone.is_naive(invalidated_at):
        invalidated_at = timezone.make_aware(invalidated_at, timezone.get_default_timezone())
    now = timezone.make_aware(datetime.datetime.now(), timezone.get_default_timezone())
    if invalidated_at < now:
        scheme, netloc, path, params, query, fragment = urlparse.urlparse(url)
        return urlparse.urlunparse(
            (scheme, cdn_domain, path, params, query, fragment))
    else:
        return url
