=========
CHANGELOG
=========

3.2.2 (2024-09-09)
==================

* fix: Remove version in to Django<5.1

3.2.1 (2024-09-05)
==================

* fix: Restore python 3.8 and python 3.9 compatibility

3.2.0 (2024-08-23)
==================

* feat: Add cache for permission checks by @fsbraun in https://github.com/django-cms/django-filer/pull/1486
* fix: Reduce number of thumbnails created for admin, avoid admin thumbnails for svg files by @fsbraun in https://github.com/django-cms/django-filer/pull/1490
* fix: Allow ``Image.MAX_IMAGE_PIXELS`` to be ``None`` by @fsbraun in https://github.com/django-cms/django-filer/pull/1475
* docs: Update extending_filer.rst by @DmytroLitvinov in https://github.com/django-cms/django-filer/pull/1488

**New contributor:**

* @DmytroLitvinov made their first contribution in https://github.com/django-cms/django-filer/pull/1488

3.1.4 (2024-07-15)
==================

* feat: Accept new `STORAGES` setting, introduced in Django 4.2 by @fsbraun in https://github.com/django-cms/django-filer/pull/1472
* feat: Replace `render` with `TemplateResponse` in admin views by @fsbraun in https://github.com/django-cms/django-filer/pull/1473
* fix: File expand url incorrect and worked not with custom image models by @fsbraun in https://github.com/django-cms/django-filer/pull/1471
* fix: Crash when moving files from a filtered directory listing by @W1ldPo1nter in https://github.com/django-cms/django-filer/pull/1482
* ci: pre-commit autoupdate by @pre-commit-ci in https://github.com/django-cms/django-filer/pull/1477


3.1.3 (2024-05-17)
==================
* Fix: Folder select widget did not render correctly with standard Django admin
  styles.

3.1.2 (2024-05-17)
==================

* Made the filer check command compatible with custom image models.
* Use the final image model's app label to determine the expand view URL.
* Prepare the image expand URL in the admin code and pass it through to the template via context.
* Fix #1377: Field `verbose_name` should use `gettext_lazy`.
* Fix: styles for django 4.2+ admin.
* Fix: Unintended scroll when clearing file widget.
* Fix: Method `ImageAdminForm.clean_subject_location()` not implemented correctly causing invokation
  of `clean()` twice.


3.1.1 (2023-11-18)
==================

* fix: Added compatibility code in aldryn_config go support setting THUMBNAIL_DEFAULT_STORAGE in django 4.2
* fix: address failing gulp ci jobs
* feat: Image dimensions update management command
* ci: pre-commit autoupdate

3.1.0 (2023-10-01)
==================

* feat: limit uploaded image area (width x height) to prevent decompression
  bombs
* feat: Canonical URL action button now copies canonical URL to the user's
  clipboard
* fix: Run validators on updated files in file change view
* fix: Update mime type if uploading file in file change view
* fix: Do not allow to remove the file field from an uplaoded file in
  the admin interface
* fix: refactor upload checks into running validators in the admin
  and adding clean methods for file and (abstract) image models.
* Fixed two more instances of javascript int overflow issue (#1335)
* fix: ensure uniqueness of icon admin url names
* fix: Crash with django-storage if filer file does not have a
  storage file attached

3.0.6 (2023-09-08)
==================

* Re-add alphabetical sorting as default (fixes #1415) by @filipweidemann in https://github.com/django-cms/django-filer/pull/1416
* fix: django-storage 1.14 complains about files being opened twice when copying by @fsbraun in https://github.com/django-cms/django-filer/pull/1418

3.0.5 (2023-08-22)
==================

* Fix bug that ignored thumbnail storage custom settings in directory view
* remove Django 2.2, 3.0, and 3.1 classifiers in setup.py
* remove tests for Django < 3.2 since those versions are not supported anymore

3.0.4 (2023-08-04)
==================

* Fix bug when submitting permission admin form
* Fix folder select field css of permission admin form
* Fix requirements (Django>=3.2) in setup.py and docs
* Update Dutch, Spanish and French locale

3.0.3 (2023-07-21)
==================

* Fix copy folder being broken after django-mptt removal by @protoroto in https://github.com/django-cms/django-filer/pull/1393
* fix: crash in the file detail view by @vinitkumar in https://github.com/django-cms/django-filer/pull/1395
* Fix: actions.js error thrown in js console by @fsbraun in https://github.com/django-cms/django-filer/pull/1397

3.0.2 (2023-07-17)
==================

* Fix another bug when the the thumbnailer in admin tags crashes because of
  invalid or missing file
* Ensure action buttons in directory listing do not get disabled after using
  cancel or back button if files or folders are selected.

3.0.1 (2023-07-13)
==================

* Fix a bug that creates a server error when requesting a thumbnail from an
  invalid or missing file
* Fix a bug that on some systems webp images were not recognized
* Add missing css map files

3.0.0 (2023-07-05)
==================

* Add validation framework to prevent XSS attacks using HTML or SVG files (see docs)
* Only show uncategorized files to the owner or superuser if permissions are active
* Add an edit button to the file widget which opens edit file pop-up
* Refactored directory list view for significant performance increases
* Remove thumbnail generation from the directory list view request response cycle
* Support for upload of webp images
* Optional support for upload of heif images
* Add Django 4.2 support
* Add thumbnail view for faster visual management of image libraries
* Fix File.objects.only() query required for deleting user who own files.
* Fix several CSS quirks
* Fix folder widget
* Remove unused css from delete confirmation view and move file view
* Add Pillow 10 compatibility
* Update translations (de/fr/nl)
* Drop Django 2.2, 3.0, and 3.1 support

2.2.5 (2023-06-11)
==================

* Security patch (https://github.com/django-cms/django-filer/pull/1352):
  While admin options shown correctly represented the user rights, some admin
  end-points were available directly. A staff user without any permissions
  could browse the filer folder structure, list files in a folder, add files,
  and move files and folders.

2.2.4 (2023-01-13)
==================
* Add Django 4.1 support
* Add python 3.11 tests
* Fix thumbnail generation for SVG images when used as a Divio addon.

2.2.3 (2022-08-08)
==================
* Fix CSS styles (Modified SCSS had to be recompiled).


2.2.2 (2022-08-02)
==================
* Fix #1305: Install django-filer with easy-thumbnail's optional SVG support.


2.2.1 (2022-06-05)
==================

* Fix: Define a ``default_auto_field`` as part of the app config.


2.2 (2022-04-20)
================

* Improve the list view of Folder permissions.
* Fix: Folder permissions were disabled for descendants, if parent folder
  has type set to CHILDREN.
* The input field for Folder changes from a standard HTML select element to
  a very wide autocomplete field, showing the complete path in Filer.
* Fix: Upload invalid SVG file.
* Add support for Python-3.10.
* Switch theme for readthedocs to Furo.
* Fix: 404 error when serving thumbnail.
* Experimental support for Django-4.


2.1.2 (2021-11-09)
==================

* In Folder permissions, make user and group autocomplete fields.
* Extent testing matrix to Python-3.10.


2.1.1 (2021-11-03)
==================

* Pin dependency for easy-thumbnails to version 2.8.0.


2.1 (2021-11-03)
================

* Remove unused legacy CSS from project.
* Remove legacy code for compatibility of old Django versions.
* Improve PermissionAdmin performance:

  * PermissionAdmin: filter by groups instead of users
  * PermissionAdmin: allow to search via user, group or folder names
  * PermissionAdmin: use prefetch_related to decrease number of DB queries

* Fix #1234: Directory listing template conflicts with djangocms-admin-style
  sidebar style.
* Fix minor styling regressions introduced in 2.1rc2.
* Fix #1227: Some icons were not aligned in the dropzone layout.
* All file/image fields render the field label.
* Fix #1232: Drag & drop of empty files results into Internal Server Error.
* Add support for SVG images. They now are handled by the model
  ``filer.imagemodels.Image`` and can be used whereever a pixel based image
  was used. This includes scaling and cropping using existing thumbnailing
  functionality from the
  `easy-thumbnails <https://easy-thumbnails.readthedocs.io/en/latest/index.html>`_
  library.
* Drop support for high resolution images and remove ``retina.js`` from project.
  High resolution images are handled by the HTML standard attribute in
  ``<img srcset="..." ... />``.
* In model ``filer.imagemodels.Image`` change ``_width`` and ``_height`` to
  Django's ``FloatFields``; this because SVG images specify their image
  extensions as floats rather than integers.
* All icons for displaying folders, files (not images) have been replaced by
  nicer looking SVG variants from `PaoMedia <https://paomedia.github.io/small-n-flat/>`_.
* Increase size of thumbnails in the admin backend's list view from 25x25 to
  40x40 pixels.
* For local development switched to NodeJS version 14.
* Add templatetag ``file_icon`` to ``file_admin_tags.py``. It now handles the
  rendering of all file types, including folders, zip-files and missing files.
* Remove pre-thumbnailing of images. Up to version 2.0, all images were scaled
  immediatly after upload into many different sizes, most of which never were
  used. Thumbnailing in the admin backend now is perfomerd lazily.
* Uploaded audio can be listened at in their detail view.
* Uploaded video files can be previewed in their detail view.
* Fix scaling of very wide but short images – causing a division by zero
  exception: ceil height to integer.
* Add method ``exists()`` to ``MultiStorageFieldFile``, which checks if a file
  exists on disk.
* Drop support of Python-3.5 (Reason: Third party requirement
  `reportlabs <https://www.reportlab.com/>`_ requires Python>=3.6).
* Fix dropzone error callback for admin fields.
* Fix #1247: Not owned files in unfiled folder can not be listed if perms are ON.
* Fix #1184: OSError close file before deletion on file move.

2.0.2 (2020-09-10)
==================

* Fix #1214: `serve()` missing 1 required positional argument: `filer_file`.
* Fix #1211: On upload MIME-type is not set correctly.


2.0.1 (2020-09-04)
==================

* Fixed NotNullViolation: null value in column "mime_type" in migration
  ``filer.0012_file_mime_type.py``.


2.0.0 (2020-09-03)
==================

* Added support for Django 3.1
* Dropped support for Python 2.7 and Python 3.4
* Dropped support for Django < 2.2
* Changed the preferred way to do model registration via model inheritance
  and ``mptt.AlreadyRegistered``, which is deprecated since django-mptt 0.4
* Use dashed name for django-polymorphic dependency in setup.py
* In ``models.File``, add field ``mime_type`` to store the Content-Type as set by
  the browser during file upload
* For extended Django Filer models, adopt the classmethod ``matches_file_type`` to its
  new signature, this is a breaking change
* Add attribute ``download`` to the download link in order to offer the file
  under its original name


1.7.1 (2020-04-29)
==================

* Fix problem with loading jquery.js after jquery.min.js had been loaded.
* Fix usability: Upload files into most recently used folder, instead of
  root folder.


1.7.0 (2020-02-20)
==================

* Added Django 3.0 support
* Added support for Python 3.8
* Add attribute ``download`` to the download link in order to offer the file
  under its original name.


1.6.0 (2019-11-06)
==================

* Removed support for Django <= 1.10
* Removed outdated files
* Code alignments with other addons
* Replace deprecated templatetag ``staticfiles`` against ``static``.
* Added management command ``filer_check`` to check the integrity of the
  database against the file system, and vice versa.
* Add jQuery as AdminFileWidget Media dependency
* Add rel="noopener noreferrer" for tab nabbing
* Fixed an issue where a value error is raised when no folder is selected
* Fixed search field overflow


1.5.0 (2019-04-30)
==================

* Added support for Django 2.2
* Adapted test matrix
* Adapted test structure and added fixes


1.4.4 (2019-01-22)
==================

* Fixed missing validation message for empty file field in file and image widget (#1125)


1.4.3 (2019-01-07)
==================

* Fixed wrong argument for AdminFileWidget render method (#1120)


1.4.2 (2019-01-07)
==================

* Fixed missing renderer argument for render method for AdminFolderWidget and
  AdminFileWidget classes for Django 2.x (#1120)
* Fixed a problem in Django 2.x with getting None instead of
  the object in AdminFileWidget and AdminFolderWidget (#1118)


1.4.1 (2018-12-06)
==================

* Fixed widgets to work with Django 2.x (#1111)
* Added admin site context to make_folder view (#1112)
* Added never_cache decorator in server views. (#1100)


1.4.0 (2018-11-15)
==================

* Added support for Django 2.0 and 2.1
* Enabled django-mptt 0.9
* Converted QueryDict to dict before manipulating in admin
* Hide 'Save as new' button in file admin
* Fixed history link for folder and image object
* Fixed rendering canonical URL in change form


1.3.2 (2018-04-23)
==================

* Don't show set public / set private actions if permissions are disabled.


1.3.1 (2018-04-15)
==================

* Allowed easy-thumbnails < 3 in setup.py
* Fixed broken reference for delete icon
* Fixed minor documentation issues
* Fixed travis configuration
* Fixed a regression with loading and dumping fixtures (#965)
* Added callable instead of setting as Filer.is_public default
* Fixed canonical URL computation
* Fixed image preview target size
* Fixed translatable string
* Updated translations
* Changed file size field to BigIntegerField
* Fixed import_files command to work on Django 1.10+
* Used get_queryset in FolderAdmin instead of the manager
* Cleaned up swapped models implementation
* Allowed django-polymorphic>_2.0


1.3.0 (2017-11-02)
==================

* Introduced Django 1.11 support
* Fixed `get_css_position` filter breaking when there is no image
* Fixed missing html title when adding folders
* Fixed a regression where third party app migrations would require the
  ``FILER_IMAGE_MODEL`` setting.


1.2.7 (2017-03-02)
==================

* Added 'get_css_position' template filter for background images
* Updated translations


1.2.6 (2017-01-13)
==================

* Fixed markup issue with editing file in admin
* Fixed error message not always showing up properly
* Added generate thumbnails management command
* Fixed dropzone styles on smaller widths
* Fixed dropzones in inlines not initializing in Django < 1.9
* Added an action button to the directory listings to download files
* Added support for Django 1.10
* Added title attribute to the file name
* Fixed an issue whereas the CSS was compiled incorrectly
* Fixed an issue where links failed to open from django CMS sideframe
* Fixes object tools placement on image detail page and removed background color and shadow
* Added edit button to image widget
* Removed arrow in breadcrumbs if no folder or name follows
* Fixed jQuery loading on file move/copy page with Django 1.9
* Fixed localization for fieldsets of ImageAdmin
* Fixed unquoting in files search


1.2.5 (2016-09-05)
==================

* Dropping or uploading an image will now fire a js change event
* Added native Divio Cloud support


1.2.4 (2016-07-06)
==================

* Fixed add/change arguments in FileAdmin.render_change_form
* Fixed minor issues which results in spurious migration generation


1.2.3 (2016-07-05)
==================

* Added a menu into django CMS projects via filer.contrib.django_cms
* Added tests for extended models
* Updated file_ptr to use string-replacement strategy for newer Djangos


1.2.2 (2016-06-23)
==================

* Fixed an issue with `file_ptr` on Django 1.9+ installations
* Addressed file_ptr issue
* Updated translation strings


1.2.1 (2016-06-23)
==================

* Rename filer picker widget upload button
* Adds missing @2x icon files
* Added missing migration #854
* Updated translations
* Fixed an issue with hashes in URLs in the wrong place
* Fixed issue where deleting a user from a project would delete their assets


1.2.0 (2016-04-26)
==================

* Drop Django 1.5 support
* Drop Python 3.3 support (now 3.4+)
* Testrunner cleanup
* Fix many regressions and bugs in Django 1.8/1.9
* Admin UI enhancements
* Fix issues with non-default STATICFILES_STORAGE
* Hide related widget wrapper links
* Fix cancel link in delete confirmation
* Make BaseImage.subject_location field non-nullable
* Adds icon sizes
* Fixes owner search icon on detail view
* Disable submit button if only one folder to copy file
* Design improvements
* Empty folder design
* Removes disabled action button border
* Adds unsorted uploads empty view
* Fix issues with subject location being off on images smaller than 210px
* Ignores unsorted uploads from search and count


1.1.1 (2016-01-27)
==================

* Fixes tests and configuration to run under Django 1.9
* Allow Django 1.9.x in setup requirements
* Fixes an issue where only the first drop-zone will be active
* Fixes an issue with Python 3 for the import_files command
* Fixes button space on delete confirmation modal
* Updates Filer image plugin form fields
* Removes folder content space in admin, side frame and modal
* Updates drag and drop modal window
* Updates drag and drop widget styles
* Fixes empty folder alignment


1.1.0 (2016-01-19)
==================

* Allow to provide single dimension for resizing images.
* Search result fixes for current folder search.
* Workaround for SQLite problems on simultaneous file uploads.
* Add missing search results counters.
* Move project to divio/django-filer.
* Adapt documentation links.
* Cleanup frontend code and adapt to guidelines.
* Added drag & drop capabilities.
* Redesign of the User Interface


1.0.6 (2015-12-30)
==================

* Fix imports for django-polymorphic>=0.8.
* Limit dependencies versions in setup.py.
* Simplify tox setup.
* Refactor Travis setup to use tox environments list.


1.0.5 (2015-12-29)
==================

* Pin django-polymorphic version.
* Use specific django-mptt versions in tox.ini for different Django versions.


1.0.4 (2015-11-14)
==================

* Repackage for PyPI.


1.0.3 (2015-11-24)
==================

* Fixes a bad static path.
* Adds a fix for Django 1.8 envs.


1.0.2 (2015-11-10)
==================

* Repackage for PyPI.


1.0.1 (2015-11-03)
==================

* Repackage for PyPI.


1.0.0 (2015-11-03)
==================

* Substantial UI/UX overhaul.
* Fixes some Django 1.9 issues.
* Drop support for Django older than v1.5.
* Fixes urls for changed files.
* Fixes an issue with KeyErrors during saving folder.
* Provides support for configuring the canonical URLs.
* Remove `FILER_STATICMEDIA_PREFIX` and use `staticfiles` for static files.
* Fixes searching for folders.
* Adds checkerboard-tile backgrounds to illustrate transparency in thumbnails.
* Other fixes.


0.9.12 (2015-07-28)
===================

* Various bugfixes.
* Better Django 1.7 and 1.8 support.

0.9.11 (2015-06-09)
===================

* Update Django 1.7 migrations because of change in django_polymorphic>=0.7.


0.9.10 (2015-05-31)
===================

* Migrations in default locations for Django 1.7 and South>=1.0.
* jQuery isolation fixes
* Various bugfixes.


0.9.9 (2015-01-20)
==================

* Fixes in Django 1.7 support.
* Implement PEP440 compliant.
* Add author to admin.
* Allow customizing dismiss popup.
* Add order_by parameter in directory listing.


0.9.8 (2014-11-03)
==================

* Experimental Django 1.7 support.
* Bugfixes.


0.9.7 (2014-07-22)
==================

* thumbnails: add zoom support.
* Fixed migration custom User compatibility.
* Disallow copying folders to self.
* Build random path using os.path.join.
* Replace use of force_str by force_text.


0.9.6 (2014-06-27)
==================

* Various bugfixes.
* Dropped support for Django 1.3.
* Added better support for Django 1.6.
* Experimental python 3.3 support.


0.9.5 (2013-06-28)
==================

* File paths now contain random component by default (to avoid filename clashes).
* Fixed migrations to be better compatible with custom user models.
* Bugfixes, performance improvements.


0.9.4 (2013-04-09)
==================

* Experimental Django 1.5 support.
* Bugfixes.


0.9.3 (2012-11-29)
==================

* Fixes template file permissions (packaging issue).


0.9.2 (2012-11-19)
==================

* File.name move to not null (run migrations).
* Fix popup mode when Folder doesn't exists.
* #271 Remove unused templatetag from django 1.4.
* #269 Hide "Folder permissions" entry for "normal" users.
* #265 click on image thumbnail in popup looses context.
* #264 cancel search button looses popup context.
* #263 deleting images from the image detail view redirects to the wrong list view.


0.9.1 (2012-10-12)
==================

* Removed nginx X-Accel-Redirect Content-Type header (#245).
* Validate_related_name method appears to break in FilerFileField (#148).
* Remember last openened folder in file picker  (#187).


0.9 (2012-09-05)
================

* Django-1.4 compatibility.
* Separate, customizable file storage backends for public and private files.
* Deleting a file in filer now deletes the file and all its thumbnails from the filesystem.
* Many bulk operations (admin actions).
* Backwards incompatible changes:
  * storage refactor: path to private files in the db has changed (no longer relative to MEDIA_ROOT)
  * `filer.server.urls` needs to be included to serve private files
  * static media has been moved from 'media' to 'static'
    (as proposed by django.contrib.staticfiles and django 1.3)
  * django 1.2 no longer supported


0.8.7 (2012-07-26)
==================

* Minor maintenance release.
* No longer unpack uploaded zip files (#172).
* Removed some print statements.


0.8.6 (2012-03-13)
==================

* Renamed media to static.
* New dependency: django-staticfiles or django >= 1.3.
* Minor bugfixes.


0.8.5 (2011-09-28)
==================

* Fix thumbnail templatetag support for easy-thumbnails>=1.0-alpha-17.


0.8.4 (2011-09-27)
==================

* Fix ajax file upload for django < 1.3.


0.8.3 (2011-08-27)
==================

* Replaced flash uploader with pure javascript (burn in hell, flash uplaoder!).


0.8.2 (2010-12-16)
==================

* Sha hash for files.
* Packaging fixes.


0.8.1 (2010-10-30)
==================

* Moved to easy-thumbnails for thumbnailing. added tests and lots of cleanup.
* Backwards incompatible changes:
  * use easy-thumbnails instead of sorl.thumbnail


0.7.0
=====

* Bugfixes


0.5.4a1
=======

* Adds description field.


0.0.2a (2009-11-04)
===================

* First test release as a pypi package.
