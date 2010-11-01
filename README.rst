============
django-filer
============


A file management application for django that makes handling of files and images a breeze.

Dependencies
------------

* django-cms >= 2.1
* easy-thumbnails >= 1.0-alpha-13

Installation
------------

add the ``django-filer`` to ``INSTALLED_APPS``::

    INSTALLED_APPS = (
        ...
        'filer',
        ...
    )

and then run ``syncdb`` or ``migrate`` if you're using South.

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
