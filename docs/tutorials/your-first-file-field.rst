======================
Your first file field
======================

In this tutorial you add a file reference to one of your own models, so that editors can pick
a file from the library — or upload a new one — from inside your own admin form.

It assumes you have finished :doc:`getting-started` and have an ambit with at least one file
in it.


Add the model field
===================

:class:`~finder.models.fields.FinderFileField` stores a reference to a file in the library.
It is a ``UUIDField`` under the hood, so it adds no join to your queries:

.. code-block:: python

    from django.db import models

    from finder.models.fields import FinderFileField


    class Article(models.Model):
        title = models.CharField(max_length=200)
        illustration = FinderFileField(
            null=True,
            blank=True,
            ambit='default',  # the slug of an existing ambit
        )

Then create and run the migration:

.. code-block:: shell

    ./manage.py makemigrations
    ./manage.py migrate


Restrict what can be selected
=============================

Pass ``accept_mime_types`` to limit the picker to certain file types:

.. code-block:: python

    illustration = FinderFileField(
        null=True,
        blank=True,
        ambit='default',
        accept_mime_types=['image/*'],
    )


Include the widget's JavaScript
===============================

Forms generated from the model render the field as the ``<finder-file-select>`` web
component. Its JavaScript has to be loaded by the page:

.. code-block:: html+django

    <script src="{% static 'finder/js/finder-select.js' %}"></script>

In the Django admin this happens automatically through the widget's ``Media`` class. On your
own frontend forms, add the tag yourself.

.. todo::

   Show a complete frontend form example — the ``demoapp`` in the repository has one at
   http://localhost:8000/demoapp/ — and say what the widget posts back.


Use the file in a template
==========================

.. code-block:: html+django

    {% load finder_tags %}

    <a href="{% download_url article.illustration_id %}">Download</a>

.. todo::

   ``finder.templatetags.finder_tags`` currently exposes only ``download_url``. Document how
   to render a thumbnail or an image at a given size from a template — at the moment that
   requires going through the model API or the ``crop`` endpoint. See
   :doc:`../reference/browser-api`.
