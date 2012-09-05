============
django-filer
============


A file management application for django that makes handling of files and images a breeze.

Documentation: http://django-filer.readthedocs.org/en/latest/index.html

Wiki: https://github.com/stefanfoulis/django-filer/wiki

Dependencies
------------

* `Django`_ >= 1.3 (with ``django.contrib.staticfiles``)
* django-mptt >= 0.2.1
* `easy_thumbnails`_ >= 1.0-alpha-17
* `django-polymorphic`_ >= 0.2
* `PIL`_ 1.1.7 (with JPEG and ZLIB support)

Installation
------------

To get started using ``django-filer`` simply install it with
``pip``::

    $ pip install django-filer


Configuration
-------------

Add ``"filer"`` and ``"easy_thumbnails"`` to your project's ``INSTALLED_APPS`` setting and run ``syncdb``
(or ``migrate`` if you're using South).

See the docs for advanced configuration:

  * `subject location docs`_
  * `permission docs`_ (experimental)
  * `secure file downloads docs`_ (experimental)


.. _Django: http://djangoproject.com
.. _django-polymorphic: https://github.com/bconstantin/django_polymorphic
.. _easy_thumbnails: https://github.com/SmileyChris/easy-thumbnails
.. _sorl.thumbnail: http://thumbnail.sorl.net/
.. _PIL: http://www.pythonware.com/products/pil/
.. _Pillow: http://pypi.python.org/pypi/Pillow/
.. _docs: http://django-filer.readthedocs.org/en/latest/index.html
.. _subject location docs: http://django-filer.readthedocs.org/en/latest/installation.html#subject-location-aware-cropping
.. _permission docs: http://django-filer.readthedocs.org/en/latest/permissions.html
.. _secure file downloads docs: http://django-filer.readthedocs.org/en/latest/secure_downloads.html
