from __future__ import unicode_literals

try:
    from django.utils.encoding import force_str
except ImportError:
    # Django < 1.5
    from django.utils.encoding import force_unicode as force_str
from django.utils.timezone import now
from filer.utils.files import get_valid_filename
from django.utils.encoding import smart_str
import os


def by_date(instance, filename):
    datepart = force_str(now().strftime(smart_str("%Y/%m/%d")))
    return os.path.join(datepart, get_valid_filename(filename))

def randomized(instance, filename):
    import uuid
    uuid_str = str(uuid.uuid4())
    random_path = "%s/%s/%s" % (uuid_str[0:2], uuid_str[2:4], uuid_str)
    return os.path.join(random_path, get_valid_filename(filename))


class prefixed_factory(object):
    def __init__(self, upload_to, prefix):
        self.upload_to = upload_to
        self.prefix = prefix

    def __call__(self, instance, filename):
        if callable(self.upload_to):
            upload_to_str = self.upload_to(instance, filename)
        else:
            upload_to_str = self.upload_to
        if not self.prefix:
            return upload_to_str
        return os.path.join(self.prefix, upload_to_str)
