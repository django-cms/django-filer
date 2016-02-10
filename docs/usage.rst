.. _usage:

Usage
======

``django-filer`` provides model fields to replace `djangos` own
`django.db.models.FileField`_ and `django.db.models.ImageField`_.
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
     company.logo.url         # prints path to original image

``FileMimetypeValidator`` and preconfigured validators
------------------------------------------------------

``django-filer`` provides a validator to allow only files of some mimetypes.
``FileMimetypeValidator`` require a mimetypes list and allow wildcard for 
subtypes. eg : `image/jpeg` allow only JPEG files, but if you want to allow all
image types, `image/*` is accepted.

Some preconfigured validators are set:

* `validate_audios` : allow all `audio/*` files
* `validate_images` : allow all `images/*` files
* `validate_videos` : allow all `video/*` files
* `validate_html5_audios` : allow most supported audio file format for web integration
  (wav, mp3, mp4, ogg, webm, aac)
* `validate_html5_images` : allow most supported image file format for web integration
  (jpeg, png, gif, svg)
* `validate_html5_videos` : allow most supported video file format for web integration
  (mp4, ogv, webm)
* `validate_documents` : allow main document types 
  (odt, ods, odpn, doc, xls, ppt, pdf, csv)


``FilerFileField`` and ``FilerImageField``
------------------------------------------

They are subclasses of `django.db.models.ForeignKey`_, so the same rules apply.
The only difference is, that there is no need to declare what model we are
referencing (it is always ``filer.models.File`` for the ``FilerFileField`` and
``filer.models.Image`` for the ``FilerImageField``).

Those Fields have some specific and optionnal options :

* `default_folder_key` : specify the folder handler key which will return the
folder where files will be stored for direct upload, or the folder to open 
when we use file lookup.
* `default_direct_upload_enabled` : Allow use to upload a file inside the
  main form (without opening the files lookup popup). Default is False
  to stay backward compatible.
* `default_file_lookup_enabled` : Allow user to choose (or add) files via
  the file lookup popup (default is True)

Simple example ``models.py``::

    from django.db import models
    from filer.fields.image import FilerImageField
    from filer.fields.file import FilerFileField

    class Company(models.Model):
        name = models.CharField(max_length=255)
        logo = FilerImageField(null=True, blank=True,
                               related_name="company_logo")
        disclaimer = FilerFileField(null=True, blank=True,
                                    related_name="company_disclaimer")

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


Advanced exemple ``models.py``::

    from django.db import models
    from filer.fields.image import FilerImageField
    from filer.fields.file import FilerFileField
    from filer.validators import FileMimetypeValidator, validate_documents

    class Company(models.Model):
        name = models.CharField(max_length=255)
        logo = FilerImageField(null=True, blank=True,
                               help_text='JPEG only',
                               default_direct_upload_enabled=True,
                               default_file_lookup_enabled=False,
                               default_folder_key='USERS_OWN_FOLDER',
                               validators=[FileMimetypeValidator(['image/jpeg',]),],
                               related_name="company_logo")
        disclaimer = FilerFileField(null=True, blank=True,
                                    default_direct_upload_enabled=True,
                                    default_file_lookup_enabled=True,
                                    default_folder_key='DOCUMENTS',
                                    validators=[validate_documents,]
                                    related_name="company_disclaimer")

templates
.........

``django-filer`` plays well with `easy_thumbnails`_ . At the template level a
``FilerImageField`` can be used the same as a regular
`django.db.models.ImageField`_::

    {% load thumbnail %}
    {% thumbnail company.logo 250x250 crop %}

admin
.....

The default widget provides a popup file selector that also directly supports
uploading new images.

.. figure:: _static/default_admin_file_widget.png
   :alt: FileField widget in admin

* Clicking on the magnifying glass will display the file selction popup.

* The red X will de-select the currently selected file (usefull if the field
  can be ``null``).

.. WARNING::
   Don't place a ``FilerFileField`` as the first field in admin. Django admin
   will try to set the focus to the first field in the form. But since the form
   field of ``FilerFileField`` is hidden that will cause in a javascript error.


.. _django.db.models.ForeignKey: http://docs.djangoproject.com/en/stable/ref/models/fields/#django.db.models.ForeignKey
.. _django.db.models.FileField: http://docs.djangoproject.com/en/stable/ref/models/fields/#django.db.models.FileField
.. _django.db.models.ImageField: http://docs.djangoproject.com/en/stable/ref/models/fields/#django.db.models.ImageField
.. _easy_thumbnails: https://github.com/SmileyChris/easy-thumbnails
