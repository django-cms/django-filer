CHANGELOG
=========

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
