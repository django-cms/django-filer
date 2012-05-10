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

* `Django`_ 1.2
* `django-mptt`_ >= 0.2.1
* `easy_thumbnails`_ >= 1.0-alpha-17
* `django-polymorphic`_ >= 0.2
* `PIL`_ 1.1.7 (with JPEG and ZLIB support) I recommend using `Pillow`_ instead.
* `django-staticfiles`_ or ``django.contrib.staticfiles`` with `Django`_ 1.3 is 
  recommended
* `ffmpeg`_ (recommended for video conversions) 

Since the `PIL`_ package on `pypi`_ can be notoriously hard to install on some
platforms it is not listed in the package dependencies in ``setup.py`` and won't
be installed automatically. Please make sure you install `PIL`_ with JPEG and
ZLIB support installed. I recommend the better packaged `Pillow`_ a better
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

By default django-filer will look for those files at ``<STATIC_URL>/filer/`` . 
Make sure that they are accessible at one of those locations. 
See the :ref:`FILER_STATICMEDIA_PREFIX` setting if you want to serve them from
somewhere else.

permissions on files
....................

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

By default files with permissions are served directly by `django`_. That is
acceptable in a development environment, but very bad for performance in
production. See the docs on :ref:`how to serve files more efficiently
<server>`.

subject location aware cropping
...............................

It is possible to define the *important* part of an image (the 
*subject location*) in the admin interface for django-filer images. This is 
very useful when later resizing and cropping images with easy_thumbnails. The 
image can then be cropped autamatically in a way, that the important part of
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

video conversion with ffmpeg
............................

If installed, `ffmpeg`_ can be used for the conversion of uploaded videos into multiple
formats, resizing of video dimensions and capture of a screenshot to use as a poster image.

The list of accepted video formats for upload is defined in the ``FILER_SOURCE_VIDEO_FORMATS`` setting. Uploaded
files with these extensions (do not include the leading dot) will be recognized by django-filer as video files. 
When using ffmpeg, this list should match the formats available for conversion.

    FILER_SOURCE_VIDEO_FORMATS = ('mp4', 'avi', 'wmv', 'mov', 'mpg')

To define the list of formats to which video files should be converted to, set the ``FILER_VIDEO_FORMATS`` setting to a list of
corresponding file extensions.

    FILER_VIDEO_FORMATS = ('flv', 'mp4','webm')

By default the videos are converted maintaining the original video dimensions. 
It is possible to :ref:`choose different dimensions in the admin interface<video_dimensions_manually>` for each video,
but if all videos should be resized to a preset dimension, the ``FFMPEG_TARGET_DIMENSIONS``
setting can be used.

    FFMPEG_TARGET_DIMENSIONS = "640x480"

The value must be a string in the format "<width>x<height>". Leave it blank to revert to
the default behaviour.

Parameters regarding the conversion quality can be adjusted in the setting
``FFMPEG_CMD``, and parameters for the capture of the poster image can be adjusted
in the setting ``GRABIMG_CMD``. Check the `ffmpeg`_ documentation for a list of available
options.

.. _cron-video:

Cron setup for video conversion
-------------------------------

Converting a video is a time consuming operation that cannot be done during
the upload of the file. When the video is uploaded it gets the conversion 
status "new". A Django management command is provided for running the 
conversion of all videos with "new" status.

    ./manage.py convert_video

This command should typically be setup in a cron job so that in regular 
intervals all newly uploaded videos get converted.


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
.. _ffmpeg: http://ffmpeg.org/
