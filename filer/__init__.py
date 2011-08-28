#-*- coding: utf-8 -*-
__version_info__ = {  # pragma: nocover
    'major': 0,
    'minor': 9,
    'micro': 0,
    'releaselevel': 'alpha',
    'serial': 1
}

def get_version(short=False):  # pragma: nocover
    assert __version_info__['releaselevel'] in ('alpha', 'beta', 'final')
    vers = ["%(major)i.%(minor)i" % __version_info__, ]
    if __version_info__['micro']:
        vers.append(".%(micro)i" % __version_info__)
    if __version_info__['releaselevel'] != 'final' and not short:
        vers.append('%s%i' % (__version_info__['releaselevel'][0], __version_info__['serial']))
    return ''.join(vers)

__version__ = get_version()  # pragma: nocover
