from django import VERSION
if VERSION[:2] >= (1, 4):
    from django.utils.timezone import now
else:
    from datetime import datetime
    def now(tz=None):
        return datetime.now(tz)
from filer.utils.files import get_valid_filename
from django.utils.encoding import force_unicode, smart_str
import os


def by_date(instance, filename):
    datepart = force_unicode(now().strftime(smart_str("%Y/%m/%d")))
    return os.path.join(datepart, get_valid_filename(filename))

def randomized(instance, filename):
    import uuid
    uuid_str = str(uuid.uuid4())
    random_path = u"%s/%s/%s" % (uuid_str[0:2], uuid_str[2:4], uuid_str)
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
