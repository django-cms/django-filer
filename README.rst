============
django-filer
============


A file management application for django that makes handling of files and images a breeze.

+-----------------------------------------------------------------------------------------------------------------+-----------------------------------------------------------------------------------------------------------------+
| .. image:: https://raw.githubusercontent.com/divio/django-filer/develop/filer/static/preview_images/filer_1.png | .. image:: https://raw.githubusercontent.com/divio/django-filer/develop/filer/static/preview_images/filer_2.png |
+-----------------------------------------------------------------------------------------------------------------+-----------------------------------------------------------------------------------------------------------------+

Filer detail view:

+----------------------------------------------------------------------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------+
| .. image:: https://raw.githubusercontent.com/divio/django-filer/develop/filer/static/preview_images/detail_image.png | .. image:: https://raw.githubusercontent.com/divio/django-filer/develop/filer/static/preview_images/detail_file.png |
+----------------------------------------------------------------------------------------------------------------------+---------------------------------------------------------------------------------------------------------------------+

Filer picker widget:

+-----------------------------------------------------------------------------------------------------------------------+-----------------------------------------------------------------------------------------------------------------------+
| .. image:: https://raw.githubusercontent.com/divio/django-filer/develop/filer/static/preview_images/file_picker_1.png | .. image:: https://raw.githubusercontent.com/divio/django-filer/develop/filer/static/preview_images/file_picker_2.png |
+-----------------------------------------------------------------------------------------------------------------------+-----------------------------------------------------------------------------------------------------------------------+
| .. image:: https://raw.githubusercontent.com/divio/django-filer/develop/filer/static/preview_images/file_picker_3.png |                                                                                                                       |
+-----------------------------------------------------------------------------------------------------------------------+-----------------------------------------------------------------------------------------------------------------------+

Documentation: http://django-filer.readthedocs.org/en/latest/index.html

Wiki: https://github.com/divio/django-filer/wiki

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

Installation
------------

To get started using ``django-filer`` simply install it with
``pip``::

    pip install django-filer


Configuration
-------------

Add ``"filer"``, ``"mptt"`` and ``"easy_thumbnails"`` to your project's ``INSTALLED_APPS`` setting and run ``syncdb``
(and ``migrate`` if you're using South).

See the docs for advanced configuration:

* `subject location docs`_
* `permission docs`_ (experimental)
* `secure file downloads docs`_ (experimental)

Django <1.7 and South
---------------------

Django 1.7+ is supported together with the new migrations. For Django<1.7 South
is still supported, you need at least South>=1.0 for South to find them though.


Testsuite
---------

For testing ``tox`` is required. See documentation for details.


Development front-end
---------------------

To started development fron-end part of ``django-filer`` simply install all the packages over npm:

``npm install``

To compile and watch scss, run javascript unit-tests, jshint and jscs watchers:

``gulp``

To compile scss to css:

``gulp sass``

To run sass watcher:

``gulp sass:watch``

To run javascript linting and code styling analysis:

``gulp lint``

To run javascript linting and code styling analysis watcher:

``gulp lint:watch``

To run javascript linting:

``gulp jshint``

To run javascript code style analysis:

``gulp jscs``

To fix javascript code style errors:

``gulp jscs:fix``

To run javascript unit-tests:

``gulp tests:unit``


.. _Django: http://djangoproject.com
.. _django-polymorphic: https://github.com/chrisglass/django_polymorphic
.. _easy_thumbnails: https://github.com/SmileyChris/easy-thumbnails
.. _sorl.thumbnail: http://thumbnail.sorl.net/
.. _django-mptt: https://github.com/django-mptt/django-mptt/
.. _PIL: http://www.pythonware.com/products/pil/
.. _Pillow: http://pypi.python.org/pypi/Pillow/
.. _docs: http://django-filer.readthedocs.org/en/latest/index.html
.. _subject location docs: http://django-filer.readthedocs.org/en/latest/installation.html#subject-location-aware-cropping
.. _permission docs: http://django-filer.readthedocs.org/en/latest/permissions.html
.. _secure file downloads docs: http://django-filer.readthedocs.org/en/latest/secure_downloads.html
