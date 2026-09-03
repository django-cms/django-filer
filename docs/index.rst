===========================
django-finder documentation
===========================

**django-finder** is a media asset management application for Django. It is the complete
rewrite of `django-filer <https://github.com/django-cms/django-filer>`_ that lives on the
``finder`` branch: a file browser in the Django admin that behaves like the file manager of
your operating system, a permission system built on access control lists, and an extension
mechanism that lets you teach it about any MIME type.

.. toctree::
   :maxdepth: 2
   :hidden:

   tutorials/index
   how-to/index
   reference/index
   explanation/index


How this documentation is organised
===================================

These pages follow the `Diátaxis <https://diataxis.fr/>`_ framework. Each section answers a
different kind of question, and knowing which one you are asking is the fastest way to the
page you need.

:doc:`Tutorials <tutorials/index>`
    Lessons that take you by the hand through getting django-finder running. Start here if
    you have never used it. They are learning-oriented: follow them in order, and do not
    worry about why each step works yet.

:doc:`How-to guides <how-to/index>`
    Recipes for a specific goal — configuring a storage backend, adding support for a file
    type, migrating from django-filer. They assume you already have a working installation
    and know roughly what you want.

:doc:`Reference <reference/index>`
    The settings, models, management commands and APIs, described exactly. Consult these
    when you need to know what something does, not how to use it.

:doc:`Explanation <explanation/index>`
    The reasoning behind the design: why the rewrite happened, why permissions are access
    control lists, why every ambit needs two storage backends. Read these to understand the
    shape of the project.


Getting help
============

* Issues and discussions: https://github.com/django-cms/django-filer
* Discord: https://www.django-cms.org/discord


Contributing
============

The code is hosted on GitHub at https://github.com/django-cms/django-filer and is fully open
source. See :doc:`explanation/why-a-rewrite` for the background, and the repository's
contribution guidelines for how to submit changes.
