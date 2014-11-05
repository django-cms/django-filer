CHANGELOG
=========

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
