=======================
Form fields and widgets
=======================

Model fields
============

``finder.models.fields.FinderFileField``
    Stores a reference to a file as a UUID. Arguments: ``ambit`` (slug, defaults to
    ``FINDER_DEFAULT_AMBIT``) and ``accept_mime_types`` (a list of patterns such as
    ``['image/*']``).

``finder.models.fields.FinderFolderField``
    Stores a reference to a folder as a UUID. Argument: ``ambit``.


Form fields
===========

``finder.forms.fields.FinderFileField``, ``finder.forms.fields.FinderFolderField``
    The form-level counterparts, used automatically by the model fields. Both accept
    ``ambit``; the file field also accepts ``accept_mime_types``.

``finder.forms.fields.TagChoiceField``
    A ``ModelMultipleChoiceField`` over the tags of an ambit.


Widgets
=======

``finder.forms.widgets.FinderFileSelect``, ``finder.forms.widgets.FinderFolderSelect``
    Render as the ``<finder-file-select>`` and ``<finder-folder-select>`` web components.
    Their JavaScript is ``finder/js/finder-select.js`` and is declared through the widget's
    ``Media`` class.

.. todo::

   Document the attributes the rendered web components accept, and the JSON shape of
   ``data-selected_file`` / ``data-selected_folder``, so that the widgets can be driven from
   a non-Django frontend.
