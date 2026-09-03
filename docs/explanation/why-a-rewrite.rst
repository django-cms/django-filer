==============
Why a rewrite
==============

django-finder is not a new major version of django-filer. It is a replacement, sharing a
repository and a distribution name but almost no code.

The original codebase had become unmaintainable — the `discussion that started the rewrite
<https://github.com/django-cms/django-filer/discussions/1348>`_ has the detail. Two problems
mattered more than the rest.

**The File and Folder models could not be used in a multi-tenant setting.** There was one
folder tree, globally. Serving several sites, or several teams, out of one installation meant
working around the model rather than with it. :doc:`ambits` is the answer to that.

**Extending the file model was theoretically possible and practically not.** django-filer
used django-polymorphic to let specialised file types exist, and the machinery was involved
enough that in the project's whole history only one specialisation was ever written — the
image model. django-finder makes adding a file type a matter of declaring a proxy model with
an ``accept_mime_types`` list; :doc:`../how-to/support-a-new-mime-type` is a page, not a
project.


Fewer dependencies
==================

django-finder does not depend on django-polymorphic, django-mptt or easy-thumbnails. Its only
hard requirement is Django itself. Everything else is optional and scoped to the file types
you actually want to handle.

Two packages are recommended rather than required. `django-cte
<https://github.com/dimagi/django-cte>`_ speeds up tree traversal, which matters for search on
large libraries. `django-entangled <https://github.com/jrief/django-entangled>`_ gives editors
a form interface onto the ``meta_data`` JSON field that every file carries.

The admin's client code has no runtime dependencies either: it compiles to two JavaScript
files, one for the admin interface and one for the frontend widget.

.. todo::

   Say what was given up in exchange. easy-thumbnails brought a template-level thumbnail API
   and a rendition cache that django-finder does not currently replace — see
   :doc:`thumbnails-and-samples` and :doc:`../reference/template-tags`.
