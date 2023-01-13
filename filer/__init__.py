"""
See PEP 386 (https://www.python.org/dev/peps/pep-0386/)

Release logic:
 1. Increase version number (change __version__ below).
 2. Check that all changes have been documented in CHANGELOG.rst.
 3. git add filer/__init__.py CHANGELOG.rst
 4. git commit -m 'Bump to {new version}'
 5. git push
 6. Assure that all tests pass on https://github.com/django-cms/django-filer/actions
 7. Create a new release on github. Create the new tag against the latest master commit and auto generate
    the release notes https://github.com/django-cms/django-filer/releases/new
 8. Publish the release and it will automatically release to pypi
"""

__version__ = '2.2.4'

default_app_config = 'filer.apps.FilerConfig'
