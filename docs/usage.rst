.. _usage:

Usage
======

``django-filer`` provides model fields to replace `djangos` own 
`django.db.models.FileField`_ and `django.db.models.ImageField`_, as well
as an additional `FilerVideoField`.
The `django-filer` versions provide the added benefit of being able to manage
the files independently of where they are actually used in your content. As such
the same file can be used in multiple places without re-uploading it multiple
times and wasting bandwidth, time and storage.

It also comes with additional tools to detect file duplicates based on SHA1
checksums.

.. Note::
   behind the scenes this field is actually just a ForeignKey to the File model
   in ``django-filer``. So you can easily access the extra metadata like this::
     
     company.disclaimer.sha1
     company.disclaimer.size
     company.logo.width
     company.logo.height
     company.logo.icons['64'] # or {{ company.logo.icons.64 }} in a template


``FilerFileField``, ``FilerImageField`` and ``FilerVideoField``
---------------------------------------------------------------

They are subclasses of `django.db.models.ForeignKey`_, so the same rules apply.
The only difference is, that there is no need to declare what model we are
referencing (it is always ``filer.models.File`` for the ``FilerFileField``, 
``filer.models.Image`` for the ``FilerImageField`` and 
``filer.models.Video`` for the ``FilerVideoField``).

Simple example ``models.py``::
    
    from django.db import models
    from filer.fields.image import FilerImageField
    from filer.fields.file import FilerFileField
    
    class Company(models.Model):
        name = models.CharField(max_length=255)
        logo = FilerImageField(null=True, blank=True)
        disclaimer = FilerFileField(null=True, blank=True)

multiple file fields on the same model::
    
    from django.db import models
    from filer.fields.image import FilerImageField
    
    class Book(models.Model):
        title = models.CharField(max_length=255)
        cover = FilerImageField(related_name="book_covers")
        back = FilerImageField(related_name="book_backs")

As with `django.db.models.ForeignKey`_ in general, you have to define a
non-clashing ``related_name`` if there are multiple ``ForeignKey`` s to the
same model.


Video formats
-------------

Django-filer can be configured to automatically convert uploaded video
files into alternative formats.

This feature needs to be activated by setting up a cron job [REF] and configuring the
desired output formats [REF].

On the Django admin interface, videos have a group(?) "Conversion" with four fields:

 - Conversion status - 
 - width, height
 - conversion logo

When a new video is uploaded, the conversion status is set to 'new'. This builds up a queue of video processing
tasks.

When the `convert_video` manage command is run, it  will search for the next file with "new" status, 
change the status to "being processed" and execute the commands to generate the alternative versions and grab a poster 
image [REF].

If all conversions are successful, the status will be set to "converted successfully". If any of the commands
fail, it will be set to "Conversion failed".

The output from these commands will be saved in the Conversion log field.

You can change the dimensions of the generated videos for each file individually in the admin.
Just input the new width and height into the respective fields and set the status to "new" to make sure it's processed
with these new dimensions.

To process again a video, reset it's status to "new" and run the convert_video manage
command manually or wait for the scheduled task to execute.

python
.......

vdeo.formats : lists all available alternative formats for a file. Only those
files existing on disk 
{'url': url, 'format':ext, 'filepath':filepath}

.original_format : 

returns a dictionary 
{'url': url, 'format': fmt, 'mimetype': mimetype}


formats_html5 - default formats that should be recognized by browsers on the video tag

format_flash - url if available, empty dict otherwise


poster  url of the poster image
{'url': '', 'format':ext, 'filepath':''}



convert - if you need to process the video programatically use this


templates
.........

``django-filer`` plays well with `easy_thumbnails`_ . At the template level a
``FilerImageField`` can be used the same as a regular 
`django.db.models.ImageField`_::
    
    {% load thumbnails %}
    {% thumbnail company.logo 250x250 crop %}

A template tag is also provided to display videos with the multiple available 
formats.

    {% load filer_video_tags %}
	{% filer_video video_obj %}

This will generate the html5 video tag with links to the multiple video formats
and fallback to flash if the flash format is available, and link to the poster
image. The filer_video tag can accept optional dimensions parameter for the 
display window (otherwise uses the video dimensions).

	{% filer_video video_obj "640x480" %}

Note: if ffmpeg is not available for converting the videos, the dimensions of 
the uploaded video are not extracted from the file and so they need to be set 
in the tag.

admin
.....

The default widget provides a popup file selector that also directly supports
uploading new images and new videos.

.. figure:: _static/default_admin_file_widget.png
   :alt: FileField widget in admin
   
* Clicking on the magnifying glass will display the file selection popup.

* The red X will de-select the currently selected file (useful if the field
  can be ``null``).

.. WARNING::
   Don't place a ``FilerFileField`` as the first field in admin. Django admin
   will try to set the focus to the first field in the form. But since the form
   field of ``FilerFileField`` is hidden that will cause in a javascript error.


.. _django.db.models.ForeignKey: http://docs.djangoproject.com/en/1.3/ref/models/fields/#django.db.models.ForeignKey
.. _django.db.models.FileField: http://docs.djangoproject.com/en/1.3/ref/models/fields/#django.db.models.FileField
.. _django.db.models.ImageField: http://docs.djangoproject.com/en/1.3/ref/models/fields/#django.db.models.ImageField
.. _easy_thumbnails: https://github.com/SmileyChris/easy-thumbnails