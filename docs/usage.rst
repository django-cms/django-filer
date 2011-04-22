Usage
======

`django-filer` provides model fields to replace `djangos` own 
`django.db.models.FileField`_.
The `django-filer` versions provide the added benefit of being able to manage
the files independently of where they are actually used in your content. As such
the same file can be used in multiple places without re-uploading it multiple
times and wasting bandwidth, time and storage.
It also comes with additional tools to detect file duplicates based on SHA1
checksums.

.. Note::
   behind the scenes this field is actually just a ForeignKey to the File model
   in django-filer. So you can easily access the extra metadata like this::
     
     mymodel.myfilerfield.sha1
     mymodel.myfilerfield.size
     mymodel.myfilerimagefield.width
     mymodel.myfilerimagefield.height
     mymodel.myfilerimagefield.icons['64'] # or {{ mymodel.myfilerimagefield.icons.64 }} in a template


FilerFileField and FilerImageField
----------------------------------

Its a subclass of `django.db.models.ForeignKey`_, so the same rules apply. The 
only difference is, that there is no need to declare what model we are
referencing (it is always ``filer.models.File`` for the ``FilerFileField`` and 
``filer.models.Image`` for the ``FilerImageField``).

Simple example models.py::
    
    from django.db import models
    from filer.fields.image import FilerImageField
    from filer.fields.file import FilerFileField
    
    class Company(models.Model):
        name = models.CharField(max_length=255)
        logo = FilerImageField(null=True, blank=True)
        disclaimer = FilerFileField(null=True, blank=True)

multiple file field on the same model::
    
    from django.db import models
    from filer.fields.image import FilerImageField
    
    class Book(models.Model):
        title = models.CharField(max_length=255)
        cover = FilerImageField(related_name="book_covers")
        back = FilerImageField(related_name="book_backs")

As with `django.db.models.ForeignKey`_ in general, you have to define a
non-clashing ``related_name`` if there are multiple ``ForeignKey``s to the
same model.



.. _django.db.models.ForeignKey: http://docs.djangoproject.com/en/1.3/ref/models/fields/#django.db.models.ForeignKey
.. _django.db.models.FileField: http://docs.djangoproject.com/en/1.3/ref/models/fields/#django.db.models.FileField
.. _django.db.models.ImageField: http://docs.djangoproject.com/en/1.3/ref/models/fields/#django.db.models.ImageField