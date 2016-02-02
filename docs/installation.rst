.. _installation_and_configuration:

Installation and Configuration
==============================

.. note:: upgrading from 0.8.7? Checkout :ref:`upgrading`.


Getting the latest release
--------------------------

The easiest way to get ``django-filer`` is simply install it with `pip`_::

    $ pip install django-filer


Dependencies
------------

* `Django`_ >= 1.5
* `django-mptt`_ >=0.6
* `easy_thumbnails`_ >= 1.0
* `django-polymorphic`_ >= 0.7
* `Pillow`_ >=2.3.0 (with JPEG and ZLIB support, `PIL`_ 1.1.7 is supported but not recommended)

``django.contrib.staticfiles`` is required.

Please note, there are some compatibility constraints that we can not enforce
through the `setup.py`. Here are the most important of them::

    Django | django-polymorphic | django-mptt
    ------ | ------------------ | -----------
    1.5    | >=0.4.1            | >=0.6,<0.8
    1.6    | >=0.5.4,           | >=0.6,<0.8
    1.7    | >=0.5.6            | >=0.6,<0.8
    1.8    | >=0.7              | >=0.7

Please make sure you install `Pillow`_ with JPEG and  ZLIB support installed;
for further information on Pillow installation and its binary dependencies,
check `Pillow doc`_.


Django <1.7 and South
.....................

Django 1.7+ is supported together with the new migrations. For Django<1.7 South
is still supported, you need at least South>=1.0 for South to find them though.


Configuration
-------------

Add ``"filer"`` and related apps to your project's ``INSTALLED_APPS`` setting and run ``manage.py syncdb``
(or ``manage.py migrate`` if you're using `South`_ or Django migrations).::

    INSTALLED_APPS = [
        ...
        'easy_thumbnails',
        'filer',
        'mptt',
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


Subject location aware cropping
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


Permissions
...........

.. WARNING:: File permissions are an experimental feature. The api may change at any time.

See :ref:`permissions` section.


Secure downloads
................

.. WARNING:: File download permissions are an experimental feature. The api may change at any time.

See :ref:`secure_downloads` section.


Canonical URLs
..............

You can configure your project to generate canonical URLs for your public files. Just include django-filer's
URLConf in your project's ``urls.py``::

    urlpatterns = [
        ...
        url(r'^filer/', include('filer.urls')),
        ...
    ]

Contrary to the file's actual URL, the canonical URL does not change if you upload a new version of the file.
Thus, you can safely share the canonical URL. As long as the file exists, people will be redirected to its
latest version.

The canonical URL is displayed in the "advanced" panel on the file's admin page. It has the form::

    /filer/canonical/1442488644/12/

The "filer" part of the URL is configured in the project's URLconf as described above. The "canonical" part can be
changed with the setting ``FILER_CANONICAL_URL``, which defaults to ``'canonical/'``. Example::

    # settings.py

    FILER_CANONICAL_URL = 'sharing/'


Debugging and logging
.....................

While by default ``django-filer`` usually silently skips icon/thumbnail
generation errors,  two options are provided to help when working with ``django-filer``:

 * ``FILER_DEBUG``: Boolean, controls whether bubbling up any ``easy-thumbnails``
   exception (typically if an image file doesn't exists); is ``False`` by default;
 * ``FILER_ENABLE_LOGGING``: Boolean, controls whether logging the above exceptions.
   It requires proper django logging configuration for default logger or
   ``filer`` logger. Please see https://docs.djangoproject.com/en/dev/topics/logging/
   for further information about Django's logging configuration.


.. _django-filer: https://github.com/divio/django-filer/
.. _staticfiles documentation: http://docs.djangoproject.com/en/stable/howto/static-files/
.. _Django: http://djangoproject.com
.. _django-polymorphic: https://github.com/bconstantin/django_polymorphic
.. _easy_thumbnails: https://github.com/SmileyChris/easy-thumbnails
.. _sorl.thumbnail: http://thumbnail.sorl.net/
.. _django-mptt: https://github.com/django-mptt/django-mptt/
.. _Pillow: http://pypi.python.org/pypi/Pillow/
.. _Pillow doc: http://pillow.readthedocs.org/en/latest/installation.html
.. _PIL: http://www.pythonware.com/products/pil/
.. _pip: http://pypi.python.org/pypi/pip
.. _South: http://south.aeracode.org/
