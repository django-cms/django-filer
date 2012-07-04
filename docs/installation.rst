.. _installation_and_configuration:

Installation and Configuration
==============================

Getting the latest release
--------------------------

The easiest way to get ``django-filer`` is simply install it with `pip`_::

    $ pip install django-filer

If you are feeling adventurous you can get 
`the latest sourcecode from github <https://github.com/stefanfoulis/django-filer/>`_

Dependencies
------------

* `Django`_ >=1.3.1,<1.5
* `django-mptt`_ >=0.5.1,<0.6
* `easy_thumbnails`_ >= 1.0
* `django-polymorphic`_ >=0.2
* `PIL`_ 1.1.7 (with JPEG and ZLIB support) I recommend using `Pillow`_ instead.
* ``django.contrib.staticfiles``

Since the `PIL package on pypi <http://pypi.python.org/pypi/PIL/>`_ can be notoriously hard to install on some
platforms it is not listed in the package dependencies in ``setup.py`` and won't
be installed automatically. Please make sure you install `PIL`_ with JPEG and
ZLIB support installed. I recommend `Pillow`_ a better
packaged fork of `PIL`_).

Configuration
-------------

Add ``"filer"`` to your project's ``INSTALLED_APPS`` setting and run ``manage.py syncdb``
(or ``manage.py migrate`` if you're using `South`_).

Note that `easy_thumbnails`_ also has database tables and needs a ``syncdb`` or 
``migrate``.

Static media
............

In order to operate properly, django-filer needs some js and css files. They
are located in the ``static/filer`` directory in the ``filer`` package. If you are 
already using `django-staticfiles`_ or `django.contrib.staticfiles`_ you're 
already set and can skip the next paragraph.

permissions on files
....................

.. warning:: File download permissions are an experimental feature. The api may change at any time.

Files with disabled permissions are your regular world readable files in
``MEDIA_ROOT``. Files with permissions are a other case however. They can only be downloaded by
authorized users. To be able to check permissions on the file downloads, a special view is used
and they are saved in a separate location (in a directory called ``smedia`` at the same level as
``MEDIA_ROOT``).

``filer.server.urls`` needs to be included in the root ``urls.py``::

    urlpatterns += patterns('',
        url(r'^', include('filer.server.urls')),
    )

By default files with permissions are served directly by the `django`_ process. That is
acceptable in a development environment, but is very bad for performance and security in
production. See the :ref:`file permission docs <server>` on how to serve files more efficiently
and how use custom storage backends.

subject location aware cropping
...............................

It is possible to define the *important* part of an image (the 
*subject location*) in the admin interface for django-filer images. This is 
very useful when later resizing and cropping images with easy_thumbnails. The 
image can then be cropped automatically in a way, that the important part of
the image is always visible.

To enable automatic subject location aware cropping of images replace 
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

To crop an image and respect the subject location::
    
    {% load thumbnails %}
    {% thumbnail obj.img 200x300 crop upscale subject_location=obj.img.subject_location %}



.. _django-filer: https://github.com/stefanfoulis/django-filer/
.. _django-staticfiles: http://pypi.python.org/pypi/django-staticfiles/
.. _django.contrib.staticfiles: http://docs.djangoproject.com/en/1.3/howto/static-files/
.. _Django: http://djangoproject.com
.. _django-polymorphic: https://github.com/bconstantin/django_polymorphic
.. _easy_thumbnails: https://github.com/SmileyChris/easy-thumbnails
.. _sorl.thumbnail: http://thumbnail.sorl.net/
.. _PIL: http://www.pythonware.com/products/pil/
.. _django-mptt: https://github.com/django-mptt/django-mptt/
.. _Pillow: http://pypi.python.org/pypi/Pillow/
.. _pip: http://pypi.python.org/pypi/pip
.. _South: http://south.aeracode.org/
