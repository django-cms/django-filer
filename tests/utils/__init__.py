from distutils.version import LooseVersion

import easy_thumbnails


if hasattr(easy_thumbnails, 'get_version'):
    ET_2 = LooseVersion(easy_thumbnails.get_version()) > LooseVersion('2.0')
else:
    ET_2 = LooseVersion(easy_thumbnails.VERSION) > LooseVersion('2.0')
