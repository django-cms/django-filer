.. _installation_and_configuration:

Installation and Configuration
==============================


.. note:: upgrading from 0.8.7? Checkout :ref:`upgrading`.


Getting the latest release
--------------------------

The easiest way to get ``django-filer`` is simply install it with `pip`_::

    $ pip install django-filer

If you are feeling adventurous you can get
`the latest sourcecode from github <https://github.com/stefanfoulis/django-filer/>`_ or add
http://stefanfoulis.github.com/django-filer/unstable_releases/ to ``find-links`` for the latest
alpha and beta releases.

Dependencies
------------

* `Django`_ >= 1.4
* `django-mptt`_ >=0.5.1
* `easy_thumbnails`_ >= 1.0
* `django-polymorphic`_ >= 0.2
* `Pillow`_ 2.3.0 (with JPEG and ZLIB support, `PIL`_ 1.1.7 is supported but not recommended)

``django.contrib.staticfiles`` is required.

**Django >= 1.6** is supported together with `django-polymorphic`_ >= 0.5.4

Please make sure you install `Pillow`_ with JPEG and  ZLIB support installed;
for further information on Pillow installation and its binary dependencies,
check `Pillow doc`_.

Configuration
-------------

Add ``"filer"`` and related apps to your project's ``INSTALLED_APPS`` setting and run ``manage.py syncdb``
(or ``manage.py migrate`` if you're using `South`_).::

    INSTALLED_APPS = [
        ...
        'filer',
        'easy_thumbnails',
        ...
    ]



Note that `easy_thumbnails`_ also has database tables and needs a ``syncdb`` or
``migrate``.

For `easy_thumbnails`_ to support retina displays (recent MacBooks, iOS) add to settings.py::

    THUMBNAIL_HIGH_RESOLUTION = True
    
If you forget this, you may not see thumbnails for your uploaded files. Adding this line and 
refreshing the admin page will create the missing thumbnails.

Static media
............

django-filer javascript and css files are managed by ``django.contrib.staticfiles``;
please see `staticfiles documentation`_ to know how to deploy filer static files
in your environment.


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

    {% load thumbnail %}
    {% thumbnail obj.img 200x300 crop upscale subject_location=obj.img.subject_location %}

permissions
...........

.. WARNING:: File permissions are an experimental feature. The api may change at any time.

See :ref:`permissions` section.

secure downloads
................

.. WARNING:: File download permissions are an experimental feature. The api may change at any time.

See :ref:`secure_downloads` section.

debugging and logging
.....................

While by default ``django-filer`` usually silently skips icon/thumbnail
generation errors,  two options are provided to help when working with ``django-filer``:

 * ``FILER_DEBUG``: Boolean, controls whether bubbling up any ``easy-thumbnails``
   exception (typically if an image file doesn't exists); is ``False`` by default;
 * ``FILER_ENABLE_LOGGING``: Boolean, controls whether logging the above exceptions.
   It requires proper django logging configuration for default logger or
   ``filer`` logger. Please see https://docs.djangoproject.com/en/dev/topics/logging/
   for further information about Django's logging configuration.


.. _django-filer: https://github.com/stefanfoulis/django-filer/
.. _staticfiles documentation: http://docs.djangoproject.com/en/stable/howto/static-files/
.. _Django: http://djangoproject.com
.. _django-polymorphic: https://github.com/bconstantin/django_polymorphic
.. _easy_thumbnails: https://github.com/SmileyChris/easy-thumbnails
.. _sorl.thumbnail: http://thumbnail.sorl.net/
.. _django-mptt: https://github.com/django-mptt/django-mptt/
.. _Pillow: http://pypi.python.org/pypi/Pillow/
.. _Pillow doc: http://pillow.readthedocs.org/en/latest/installation.html
.. _pip: http://pypi.python.org/pypi/pip
.. _South: http://south.aeracode.org/
