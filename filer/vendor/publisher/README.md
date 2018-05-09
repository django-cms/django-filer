# Vendored djangocms-publisher

FIXME: update the url to github
Current djangocms-publisher commit used: https://github.com/divio/djangocms-publisher/tree/70a85dcb06af5783182ba7dcce8a52fe75b99ca6

This package contains some vendored in parts of the djangocms-publisher
package. They are vendored in here, because filer only needs a subset
of the features and does not depend on django-cms (djangocms-publisher
does).

Having the needed parts vendored in here also allows django-filer to be
developed at a different pace than djangocms-publisher and the other
apps using it.

To keep this maintainable the files copied in here should not be
altered. If changes are necessery they should be done with a subclass.
If that does not work the changes need to be clearly marked in the code
