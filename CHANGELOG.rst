CHANGELOG
=========

Revision 47a0d53 (28.10.2015, 12:04 UTC)
----------------------------------------

* LUN-2647

  * history button made yellow

No other commits.

Revision 5352d52 (13.10.2015, 13:15 UTC)
----------------------------------------

* LUN-2643

  * Prevent access to image/file changelist views.
  * Remove useless stuff.
  * Revert fix as view will not be accessible.
  * . Remove the option to add files/images from their changelist/change admin view.
  * Move styling fix so it will be used in both image and file changelists.
  * Remove the "Add image" link from the admin/filer/image changelist view.
  * Handle case when view is reached without an object.

* Misc commits

  * Update server_backends.py. Replace deprecated method.

Revision 49fdf9b (01.10.2015, 12:23 UTC)
----------------------------------------

No new issues.

* Misc commits

  * Add migration 0002.
  * Fixed related lookup popup icons

Revision df8010a (24.09.2015, 11:12 UTC)
----------------------------------------

No new issues.

* Misc commits

  * Django 1.8: fixed popup opening for add folder
  * Django 1.8: updated extra context for custom admin view
  * Django 1.8 upgrade: removed some django1.9 deprecation warnings
  * Django 1.8 upgrade: updated test settings & fixed file/folder model related fields

Revision 6cbcd3b (12.09.2015, 11:23 UTC)
----------------------------------------

* LUN-2620

  * resize file/folder plugin popup

No other commits.

Revision eef2065 (04.09.2015, 09:05 UTC)
----------------------------------------

* LUN-2569

  * 6.Revisit the layout of the filer upload pop-up window

* LUN-2580

  * fixes on sidebar

* LUN-2596

  * left align fieldsets

* LUN-2603

  * save button should appear when creating new folders on Filer

No other commits.

Revision 017a043 (28.08.2015, 08:51 UTC)
----------------------------------------

* LUN-2309

  * collapsible fieldset style fix
  * changed restricted link color changed
  * add error messages wrapper only if they exist
  * remove submit buttons padding around wrapper
  * submit buttons updates
  * updated manifest.in and .gitignore
  * removed .sass-cache files
  * filer updates for small resolutions and bug fixes
  * updates after django upgrade
  * remove deprecated function get_ordered_objects()
  * Filer updates on forms
  * Filer forms updates
  * re-structure of change forms
  * default boostrap updates
  * Ace resources added to plugin
  * updates on edit, delete pages
  * Filer refactoring

* Misc commits

  * Add .iml files to gitignore.
  * Restore check for permission before rendering save buttons.
  * copy-folder form updates

Revision 0aca38c (03.08.2015, 09:19 UTC)
----------------------------------------

* LUN-1434

  * -celery-task Added tests for trash management command.
  * -celery-task Added celery task for take_out_filer_trash command.

* LUN-2124

  * Small optimization since this error in improbable.
  * Added tests for restriction changes.
  * Updated tests to expect warning messages instead of permission denied.
  * Added warning messages for some possible incorrect usage cases.

* LUN-2156

  * Fixed widgets name clash.
  * Refactor imports
  * Adding new line
  * Do not show Clear checkbox on Filer asset details form

* Misc commits

  * added filer status command to check all files on storage

Revision 9c535d2 (24.07.2015, 14:46 UTC)
----------------------------------------

No new issues.

* Misc commits

  * Django 1.7 upgrade: Folder widget should be visible.

Revision 3a18983 (17.07.2015, 13:47 UTC)
----------------------------------------

No new issues.

* Misc commits

  * tox: Don't allow django 1.8 prereleases
  * Django 1.7 upgrade: fixed dummy model for admin index page
  * django 1.7 upgrade: fixed trash feature & deprecation warnings
  * Django 1.7 upgrade; regenerated migrations
  * Django 1.6 upgrade; fixed sites allowed on move action
  * Django 1.6 upgrade changes

Revision 9bdd109 (08.04.2015, 08:55 UTC)
----------------------------------------

No new issues.

* Misc commits

  * django-mptt 0.7.1 was released recently, it doesn't work out of the box

Revision 553cd36 (11.03.2015, 10:41 UTC)
----------------------------------------

No new issues.

* Misc commits

  * Fix success message

Revision b594c8f (03.03.2015, 12:20 UTC)
----------------------------------------

* LUN-1426

  * fixed tests for folder destination filtering
  * added destination cacndidates tree view for move action

* LUN-1587

  * displayed error mesages for zip extract process
  * files with image extension but without valid image data will be ignored upon extraction.

* Misc commits

  * deleted pytest leftovers
  * added destination field to copy action template

Revision db6f7e5 (06.02.2015, 12:23 UTC)
----------------------------------------

No new issues.

* Misc commits

  * convert both str & unicode to unicode

Revision d7f700c (05.11.2014, 16:58 UTC)
----------------------------------------

* LUN-1934

  * fixed circular import reproducible when DEBUG is False * this happend while running management command from other apps that depend on filer.

No other commits.

Revision 77bf2d1 (21.10.2014, 11:16 UTC)
----------------------------------------

No new issues.

* Misc commits

  * Switch the import order to avoid a circular dependcy in case filer.models is imported before filer.fields.image

Revision 2606d5f (30.09.2014, 13:35 UTC)
----------------------------------------

No new issues.

* Misc commits

  * Avoid upgrade to easy-thumbnails 2.x.x versions since would break the tests

Revision a58cd5e (06.08.2014, 07:56 UTC)
----------------------------------------

* LUN-1762

  * append popup params to files thumbnails

No other commits.

Revision ad5508f (13.06.2014, 12:26 UTC)
----------------------------------------

No new issues.

* Misc commits

  * Set correct destination for test results in tox.ini

Revision cdfe111 (17.04.2014, 12:31 UTC)
----------------------------------------

Changelog history starts here.
