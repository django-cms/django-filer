# general
rename "draft" to "not published"
rename "pending changes" to "unpublished changes"

default string representation of objects should contain "[not published]" at the end.


# list view (Directory Browser)

list view action: publish

"pending deletion" in default red
label in same warning yellow as in cms


# detail view

"pending deletion" label on detail view as well

remove "cancel" on draft detail

"request deletion" at the left with bucket icon
"discard deletion" at the left

"edit" blue right
"cancel" on live on the right (to the left of "edit")

"publish"/"publish deleteion": tooltip "Permissions needed"


# picker

drafts should have a disabled arrow picker with "not published yet" tooltip at the front

clicking on "not published yet" or "unpublished changes" should allow navigating and publishing without loosing the "picker" context.

~~find another icon for the pick. file label no longer picks~~ (to be consistent with folder)
pick draft version from detail page. right of file name. "Choose file"
pick folder on top of folder list.

"choose this file" as a button next to file name on file detail. (don't loose the picker context when publishing/navigating!)
