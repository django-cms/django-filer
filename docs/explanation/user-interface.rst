==============
User interface
==============

The admin interface deliberately mimics the file manager of a desktop operating system, on the
grounds that everyone already knows how one of those works. Files and folders are opened by
double-clicking, moved by dragging, selected by rubber-banding a rectangle over them, cut and
pasted between folders, and deleted into a trash folder they can be restored from.

It is built with `React <https://react.dev/>`_ and `dnd kit <https://dndkit.com/>`_, and
compiles to two dependency-free JavaScript bundles — one for the admin, one for the frontend
file-selection widget.


Four ways to look at a folder
=============================

**Tiles** shows everything as a flat grid of reasonably large tiles. **Mosaic** is the same
idea at a much smaller size, for scanning a folder with hundreds of images. **List** gives one
row per item with detailed columns. **Column** shows the current folder alongside each of its
ancestors, which makes moving a file several levels up a matter of one drag.


Favourite folders
=================

A user can pin any number of folders as tabs in the navigation bar, and drag files from the
current listing straight onto a tab to move them there.


The trash
=========

Deleting moves an inode to the ambit's trash folder — one per user — rather than erasing it.
It can be restored to where it came from, or deleted permanently from there.

.. todo::

   Document the keyboard shortcuts, the search interface and tag filtering, all of which the
   client implements but nothing describes.

.. todo::

   Replace the django-filer screenshots in ``_static`` with screenshots of this interface, and
   illustrate the four views.
