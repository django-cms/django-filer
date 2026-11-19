.. _provenance:

Image provenance
================

.. versionadded:: 3.7

Images increasingly come from generative AI tools, and regulations such as
`Article 50 of the EU AI Act
<https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=celex%3A32024R1689>`_
require transparency about AI-generated or AI-edited content. Two standards
mark such images inside the file:

* The **IPTC digital source type** (``Iptc4xmpExt:DigitalSourceType``), a
  property of the image's XMP metadata. Its value is a term of the `IPTC
  vocabulary <https://cv.iptc.org/newscodes/digitalsourcetype/>`_, e.g.
  ``trainedAlgorithmicMedia`` for an image created using generative AI.
* **C2PA Content Credentials**, a signed manifest store embedded in the file
  that records where the image comes from and how it was edited (see the
  `C2PA specification <https://spec.c2pa.org/>`_).

django-filer detects both when an image is uploaded, stores the result with the
image, and shows it in the admin. It works with the digital source type: this is
what editors see, filter by and can change, and what thumbnails carry. Content
Credentials are signed and bound to the uploaded file, so they stay with the
original and can neither be changed nor passed on to thumbnails. django-filer
never changes how an image looks.

.. note::

    django-filer provides information, not compliance. Whether and how you
    need to disclose AI-generated content depends on your role and use case;
    marking images on your site is up to your templates.


What is detected
----------------

Digital source type
    Read from the image's XMP packet. All common ways of writing the property
    are understood (as an attribute, as element text or as an ``rdf:resource``
    reference), whatever namespace prefix is used. A bare term such as
    ``trainedAlgorithmicMedia`` is expanded to the full IPTC URI
    ``http://cv.iptc.org/newscodes/digitalsourcetype/trainedAlgorithmicMedia``.
    Values that are neither a term nor an ``http(s)`` URI, and values longer
    than 255 characters, are ignored.

    Supported formats: JPEG, PNG, GIF, WebP, and AVIF and HEIF if Pillow can
    open them (see :ref:`installation_and_configuration`). For PNG and GIF,
    django-filer reads the XMP packet from the file itself, wherever it is
    stored, without decoding the image.

    If the XMP packet states no digital source type, the one stated by the
    image's Content Credentials is used instead (see below).

Content Credentials
    django-filer detects whether a C2PA manifest store is embedded in the
    file. It does **not** validate its signature: the information tells that
    credentials were present, not that they are genuine. Use a tool such as
    `Verify <https://verify.contentauthenticity.org/>`_ to inspect them.

    For images without an XMP digital source type, django-filer looks up the
    ``digitalSourceType`` the manifest store's actions state. It searches the
    store for it without parsing it completely. A manifest store records the
    history of an image and may state several digital source types: one
    denoting generative AI takes precedence, otherwise the last one is used.
    Being unverified, this is as reliable as the XMP property, which anyone can
    set, and no more.

    Supported formats: JPEG (APP11 segments), PNG (``caBX`` chunk), GIF
    (``C2PA_GIF`` application extension), WebP (``C2PA`` chunk), and AVIF and
    HEIF (C2PA ``uuid`` box). Manifests stored outside the file ("remote
    manifests") are not detected.

Detection is best effort: a malformed or unreadable file never makes an upload
fail, it simply yields no provenance information. SVG images carry none.


When detection runs
-------------------

* Provenance is detected whenever an image's file is set: on upload through the
  admin (drag and drop, the upload button or the change form), when an image
  is created in code, and when the file of an existing image is replaced.
  Replacing the file replaces the provenance information, too, including a
  digital source type set by a user.
* Detection sees the file **as uploaded**, before any upload validator such as
  ``strip_exif`` changes it (see :ref:`validation`).
* Images uploaded before django-filer detected provenance have none recorded.
  Scan them with the ``filer_detect_provenance`` management command (see
  :ref:`provenance_command` below).


How it is stored
----------------

Every image model (``BaseImage`` and therefore any custom
``FILER_IMAGE_MODEL``) has these fields:

``digital_source_type``
    The full IPTC URI, or an empty string if the image states none. Users can
    change it, see :ref:`provenance_editing`.

``digital_source_type_edited``
    ``True`` if a user set or removed the digital source type. Read-only.

``has_content_credentials``
    ``True`` if the uploaded file embedded a C2PA manifest store. Read-only.

Two properties make them easier to use:

``is_ai_generated``
    ``True`` if the digital source type states that the image was created or
    edited using generative AI. By default, these are the IPTC terms
    ``trainedAlgorithmicMedia`` ("Created using generative AI") and
    ``compositeWithTrainedAlgorithmicMedia`` ("Edited using generative AI").
    Other terms, e.g. ``algorithmicMedia`` for purely algorithmic images not
    based on training data, or ``compositeSynthetic``, do not count. The IPTC
    vocabulary is revised from time to time: ``FILER_AI_DIGITAL_SOURCE_TYPES``
    changes which terms count.

``digital_source_type_label``
    A human-readable, translatable label for the digital source type, e.g.
    "Original digital capture". Terms outside the IPTC vocabulary are shown as
    they are.

The fields describe the image asset in the database. They stay with it no
matter which thumbnails or other variants are generated from it.


.. _provenance_editing:

Changing the digital source type
--------------------------------

The metadata of an image may be missing or wrong. Editors can therefore set,
change or remove the digital source type on the image's change form in the
admin, e.g. to mark an image as created using generative AI. By default, the
form offers the two digital source types denoting generative AI and "Not
specified"; ``FILER_DIGITAL_SOURCE_TYPE_CHOICES`` changes that. An image whose
metadata states another digital source type, e.g. an original digital capture,
keeps it: it is offered for that image, too, and only changes if the editor
chooses another one. In code, use::

    image.set_digital_source_type("trainedAlgorithmicMedia")  # or a URI, or ""
    image.save()

* The change is stored in the database. The uploaded file is **not** changed:
  rewriting its metadata would invalidate its Content Credentials.
  ``has_content_credentials`` cannot be changed.
* Thumbnails carry the digital source type stored in the database. When it
  changes, django-filer deletes the image's thumbnails, so they are generated
  again with the new value, or without one.
* ``digital_source_type_edited`` records that a user made the choice.
  ``filer_detect_provenance`` then leaves the digital source type alone, also
  if the user removed it.
* Uploading a new file for the image replaces the digital source type with the
  one detected in that file, unless it is changed in the same form.

.. note::

    If you use a custom image model, run ``makemigrations`` for its app after
    upgrading: the fields are added to ``BaseImage``.


What happens to the metadata in files
-------------------------------------

.. list-table::
   :header-rows: 1

   * -
     - Digital source type (XMP)
     - Content Credentials (C2PA)
   * - Original, stored as uploaded
     - kept
     - kept
   * - Original, sanitized by ``strip_exif``
     - kept (unless disabled)
     - removed
   * - Original, resized by the admin's resize action
     - kept
     - removed
   * - Thumbnails and other variants
     - kept
     - removed
   * - Database fields of the image
     - kept
     - kept

Originals
    By default, django-filer stores the uploaded file byte for byte. All
    metadata, including XMP and C2PA manifests, remains in the file served as
    the original, e.g. via its canonical URL or a download link.

``strip_exif``
    The optional ``strip_exif`` upload sanitizer removes metadata to protect
    privacy. It keeps the digital source type: it writes a minimal XMP packet
    back into the file that holds this one property and nothing else, so no
    other XMP information, such as creator names or locations, survives. Set
    ``FILER_STRIP_EXIF_KEEP_DIGITAL_SOURCE_TYPE = False`` to remove it, too.

    C2PA manifests are always removed: their signature covers the original
    bytes, so a re-encoded file cannot carry them. Since detection runs before
    the sanitizer, ``has_content_credentials`` still records that the upload
    had them; the admin says "found on upload". If the image has no XMP
    digital source type, the one stated by the removed Content Credentials is
    written into the file.

Thumbnails and variants
    Thumbnails are re-encoded by easy-thumbnails, which drops all metadata of
    the original. django-filer writes the image's digital source type back into
    every thumbnail it generates, in the same minimal XMP packet ``strip_exif``
    uses, so that a thumbnail served on its own is still marked, e.g., as
    created using generative AI. The value comes from the database field,
    which also makes this work for images whose stored original no longer
    carries it, whose Content Credentials state it, or for which a user set
    it. This covers JPEG, PNG, GIF and WebP thumbnails, and AVIF and
    HEIF where Pillow can write XMP into them. SVG thumbnails carry none.

    This applies to thumbnails generated through django-filer: the admin's
    icons and previews, the ``thumbnail`` template tag of easy-thumbnails used
    with a filer image or its ``file``, and thumbnail options. Thumbnails
    generated before upgrading keep no metadata until they are regenerated.
    To have them regenerated, delete them, e.g., for AI-generated images::

        for image in Image.objects.filter(ai_digital_source_type_q()):
            image.file.delete_thumbnails()

    C2PA manifests are not copied: a manifest signed for the original would not
    match a resized, cropped or converted image.

Resize action
    The admin's "Resize selected images" action replaces the original with a
    re-encoded, resized file. Like thumbnails, it keeps the digital source type
    and loses the Content Credentials. The database fields keep describing the
    uploaded image: ``has_content_credentials`` stays set.


In the admin
------------

* The image's change form shows the **Origin** (the label of the digital source
  type) and whether **Content Credentials** were found on upload. Its
  **Digital source type** field changes the origin, see
  :ref:`provenance_editing`.
* The directory listing marks AI-generated and AI-edited images with an **AI**
  icon next to their name, in the table and in the thumbnail view. Its tooltip
  tells the digital source type. ``FILER_AI_DIGITAL_SOURCE_TYPES`` sets which
  digital source types are marked. Others, e.g. an original digital capture,
  are shown on the change form only.
* The search options of the directory listing can **filter by digital source
  type**: all images created or edited using generative AI, or the images of
  one specific digital source type of ``FILER_DIGITAL_SOURCE_TYPE_CHOICES``,
  by default those created and those edited using generative AI. The filter
  searches all folders unless "Limit the search to current folder" is checked,
  and can be combined with a search term. Since it acts on the digital source
  type, it follows the changes users make.

django-filer never adds icons, labels or watermarks to the images themselves.


Disclosing AI-generated images on your site
-------------------------------------------

Use ``is_ai_generated`` in your templates to disclose AI-generated images the
way your site requires, e.g. in a caption:

.. code-block:: html+django

    <figure>
        <img src="{{ image.url }}" alt="{{ image.default_alt_text }}">
        {% if image.is_ai_generated %}
            <figcaption>{{ image.digital_source_type_label }}</figcaption>
        {% endif %}
    </figure>

To query images, filter on the fields. ``ai_digital_source_type_q()`` builds
the condition used by ``is_ai_generated``:

.. code-block:: python

    from filer.models import Image
    from filer.utils.provenance import ai_digital_source_type_q

    ai_images = Image.objects.filter(ai_digital_source_type_q())
    with_credentials = Image.objects.filter(has_content_credentials=True)

Remember that the information comes from the uploaded file: an image without
metadata is not necessarily a photograph, and metadata can be removed or set
by anyone editing the file. Only a validated C2PA manifest proves where an
image comes from.


.. _provenance_command:

Scanning existing images
------------------------

To detect the provenance of images uploaded before, run::

    ./manage.py filer_detect_provenance

The command reads the stored files and only **adds** missing information: it
never clears a digital source type or the Content Credentials flag, since
``strip_exif`` may have removed them from the stored file after they were
recorded. A digital source type set or removed by a user is kept.
``--dry-run`` reports what would be updated, ``-v 2`` lists the images. Images
whose files cannot be read are reported and skipped. The command does not
delete thumbnails: see "Thumbnails and variants" above for how to have them
generated again.

The command can only find what the stored files still contain. If
``strip_exif`` was active when older images were uploaded, it removed both
from their files, and the command cannot recover them.


Settings
--------

``FILER_STRIP_EXIF_KEEP_DIGITAL_SOURCE_TYPE``
    Defaults to ``True``. Whether ``strip_exif`` writes the digital source type
    back into sanitized images.

``FILER_AI_DIGITAL_SOURCE_TYPES``
    The digital source types, as IPTC terms or URIs, that mark an image as
    created or edited using generative AI: they decide on ``is_ai_generated``,
    the "AI" label and the generative AI filter. Defaults to
    ``("trainedAlgorithmicMedia", "compositeWithTrainedAlgorithmicMedia")``.

``FILER_DIGITAL_SOURCE_TYPE_CHOICES``
    The digital source types, as IPTC terms or URIs, that the admin offers to
    set for an image and to filter by. Defaults to
    ``FILER_AI_DIGITAL_SOURCE_TYPES``.
    It does not restrict what is detected and stored: images keep any other
    digital source type their metadata states.
