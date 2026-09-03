=======================
Thumbnails and samples
=======================

django-finder generates its own renditions rather than depending on easy-thumbnails. Every
ambit therefore has two storage backends: the *original* storage, holding exactly what was
uploaded, and the *sample* storage, holding everything derived from it.

The split is what makes the sample storage disposable. Nothing in it is authoritative:
deleting the whole bucket costs regeneration time and nothing else. It also lets renditions
live somewhere cheaper, or behind a different CDN, than the originals.


Generation is lazy
==================

Nothing is generated on upload. A rendition is produced the first time something asks for its
URL, written to the sample storage under a deterministic filename, and served from there
afterwards. The existence check on that filename *is* the cache.

The filename encodes everything that went into the rendition — the requested size, and for
images the crop box and gravity. Changing a crop therefore produces a new filename rather than
invalidating an old one, and the old rendition simply stops being referenced.


Art direction, not just scaling
===============================

An image model stores more than a focal point. Alongside its width and height it keeps a crop
box — ``crop_x``, ``crop_y``, ``crop_size`` — and a ``gravity``, the compass direction the
crop should favour when it has room to move.

That is enough to do `art direction
<https://www.smashingmagazine.com/2016/01/responsive-image-breakpoints-generation/>`_: the
same canonical image can yield a wide banner and a tall portrait crop that both keep the
subject, instead of one centre crop that works for neither. The rules the cropping geometry
follows:

* The rendition always contains at least the main area of interest — unless the requested
  aspect ratio is narrower than that area, in which case it is cropped to that area's centre.
* The crop is never scaled up beyond the resolution available in the original, so renditions
  do not go soft.

If an editor sets no crop box, the geometry falls back to a centred square.


Per file type
=============

The four hooks a file model may implement — ``get_download_url``, ``get_thumbnail_url``,
``get_preview_url`` and ``get_sample_url`` — mean "the original", "a small square for the
listing", "something larger for the detail view" and "a playable excerpt". A model that
implements none of them gets a static icon, which is the right answer for a zip file.

Images produce real thumbnails by cropping and scaling. Video produces a poster frame and a
short clip through ffmpeg. Audio produces an excerpt. Everything else is an icon.

.. todo::

   Nothing prunes the sample storage when a crop changes: the previous rendition stays behind
   forever, and there is no cleanup command. Document the consequence, and link to a
   maintenance recipe once one exists.

.. todo::

   Explain the fixed 180-pixel thumbnail size and how to obtain other sizes — currently only
   the ``crop`` endpoint in :doc:`../reference/browser-api` does that, and there is no
   template-level API at all.

.. todo::

   ``finder.contrib.image.pil`` downscales any upload wider than 3840 pixels and overwrites
   the stored original. Explain that this is lossy and not reversible, and why the limit
   exists.
