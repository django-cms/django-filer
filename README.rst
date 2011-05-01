============
django-filer
============


A file management application for django that makes handling of files and images a breeze.

Documentation: http://django-filer.readthedocs.org/en/latest/index.html

Wiki: https://github.com/stefanfoulis/django-filer/wiki

Dependencies
------------

* `Django`_ 1.2 with django-staticfiles or `Django`_ 1.3
* django-mptt >= 0.2.1
* `easy_thumbnails`_ >= 1.0-alpha-17
* `PIL`_ 1.1.7 (with JPEG and ZLIB support)

Installation
------------

To get started using ``django-filer`` simply install it with
``pip``::

    $ pip install django-filer

Add ``"filer"`` to your project's ``INSTALLED_APPS`` setting and run ``syncdb``
(or ``migrate`` if you're using South).

Configuration
-------------

django-filer supports permissions on files. They can be enabled or disabled.
Files with disabled permissions are your regular world readable files in
``MEDIA_ROOT``. Files with permissions are a other case however. To be able to
check permissions on the file downloads a special view is used and they are
saved in a separate location (in a directory called `smedia` next to
``MEDIA_ROOT`` by default).

``filer.server.urls`` needs to be included in the root ``urls.py``::

    urlpatterns += patterns('',
        url(r'^', include('filer.server.urls')),
    )

By default files with permissions are served directly by django. That is
acceptable in a development environment, but very bad for performance in
production. See the docs on how to serve files more efficiently.


For automatic subject location aware cropping of images replace 
``easy_thumbnails.processors.scale_and_crop`` with
``filer.thumbnail_processors.scale_and_crop_with_subject_location`` in the
``THUMBNAIL_PROCESSORS`` setting::

    THUMBNAIL_PROCESSORS = (
        'easy_thumbnails.processors.colorspace',
        'easy_thumbnails.processors.autocrop',
        #'easy_thumbnails.processors.scale_and_crop',
        'filer.thumbnail_processors.scale_and_crop_with_subject_location',
        'easy_thumbnails.processors.filters',
    )

.. _Django: http://djangoproject.com
.. _easy_thumbnails: https://github.com/SmileyChris/easy-thumbnails
.. _sorl.thumbnail: http://thumbnail.sorl.net/
.. _PIL: http://www.pythonware.com/products/pil/
.. _Pillow: http://pypi.python.org/pypi/Pillow/
