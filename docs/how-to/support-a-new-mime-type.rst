=========================
Support a new MIME type
=========================

django-finder picks a model for each upload by matching its MIME type against the
``accept_mime_types`` of every registered model. Teaching it about a new type means adding a
model — usually a proxy model, so it needs no table of its own.


Add the model
=============

.. code-block:: python

    from django.utils.translation import gettext_lazy as _

    from finder.models.file import FileModel


    class FontFileModel(FileModel):
        accept_mime_types = ['font/woff2', 'font/ttf']
        fallback_thumbnail_url = staticfiles_storage.url('myapp/icons/file-font.svg')

        class Meta:
            proxy = True
            app_label = 'finder'
            verbose_name = _("Font")
            verbose_name_plural = _("Fonts")

``app_label = 'finder'`` is required: it is what puts the model in the same table family as
every other inode.

Matching is most-specific-first — an exact type wins over a ``type/*`` wildcard, which wins
over the ``*/*`` fallback of :class:`~finder.models.file.FileModel`.


Register it in the admin
========================

.. code-block:: python

    from django.contrib import admin

    from finder.admin.file import FileAdmin


    admin.site.register(FontFileModel, FileAdmin)


Give it a thumbnail
===================

Override :meth:`get_thumbnail_url` to return something better than the fallback icon, and
write the generated file to the ambit's sample storage:

.. code-block:: python

    def get_thumbnail_url(self, ambit):
        path = f'{self.id}/preview.png'
        if not ambit.sample_storage.exists(path):
            ...  # render, then ambit.sample_storage.save(path, handle)
        return ambit.sample_storage.url(path)

See :doc:`../explanation/thumbnails-and-samples` for the surrounding contract, including
``get_preview_url`` and ``get_sample_url``.


Extract metadata on upload
==========================

Override ``store_and_save`` to read properties out of the payload and record them:

.. code-block:: python

    def store_and_save(self, ambit, **kwargs):
        try:
            ...  # inspect ambit.original_storage.open(self.file_path)
        except Exception:
            pass
        else:
            if 'update_fields' in kwargs:
                kwargs['update_fields'].append('meta_data')
        super().store_and_save(ambit, **kwargs)

.. todo::

   Work a complete, runnable example through this page — ideally the font model above, from
   an empty app to a working thumbnail — and say which of ``browser_component``,
   ``editor_component`` and ``folderitem_component`` a new type needs, and what happens if
   they are left as ``None``.

.. todo::

   Explain when a proxy model is not enough and you need extra fields, using
   ``finder.contrib.image.models.ImageFileModel`` (a concrete model with its own table) as
   the worked example.


Run reorganize
==============

Files uploaded before your model existed are still attached to the previous best match. Move
them over:

.. code-block:: shell

    ./manage.py finder reorganize <ambit-slug>
