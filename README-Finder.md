# Django-Filer ("Finder" branch)

The "Finder" branch of django-filer is a complete rewrite of the original **django-filer** project.

A rewrite was necessary because the original codebase was not maintainable anymore. Please read this
[discussion](https://github.com/django-cms/django-filer/discussions/1348) for details. Apart from the maintainability issues, using the File and Folder
models was not possible in a multi-tenant environment. Extending the file model with a more
specialized implementation was possible in theory, but so complicated that apart from the
`ImageModel` no other implementations ever have been created.


## Less third-party dependencies

The "Finder" branch of **django-filer** has less third-party dependencies. It does not depend on
[django-polymorphic](https://django-polymorphic.readthedocs.io/en/stable/),
[django-mptt](https://django-mptt.readthedocs.io/en/latest/) and
[easy-thumbnails](https://easy-thumbnails.readthedocs.io/en/latest/) anymore.

For large datasets [django-cte](https://github.com/dimagi/django-cte) is reccomended, in order to improve the speed
of tree travesals, which is important while searching.

Since each `FileModel` contains a `JSONField` to store arbitrary data, [django-entangled](https://github.com/jrief/django-entangled)
is reccomended, in order to give users the opportunity to edit the contents of that field.

The client part of the new admin user interface has no runtime dependencies. It is compiled into two
JavaScript files, which are included by the corresponding admin views. One of them is used for the
django-admin interface, the other one for the frontend. The frontend part is also used for the new
file selection widget.


## Extensibility

The "Finder" branch of django-filer is designed to be extensible for every MIME-type one desires.
Therefore, those extensions might need their own dependencies in order to extract or visualize a
certain type of file. A minimal installation can be configured to only distinguish between files
and folders.


## Multiple Ambits to hold Folder Roots

The "Finder" branch of **django-filer** allows multiple ambits, each able to hold multiple root
folders. Such an ambit must be created using the management command `manage.py finder add-ambit …`.
Each ambit has a slug and a name. The slug is used in the URL to access that ambit, while the name
is used for display purposes. All ambits are displayed in the left sidebar of the Django admin. For
each ambit, a different Django storage can be configured.


## New Model Features

The "Finder" branch introduces a new model named `InodeModel`. This is the base class for all other
models, such as the `FileModel`, the `FolderModel` and all other specialized implementations. By
using a UUID instead of a numerical primary key, it is possible to use different database tables
while preserving the possibility to perform queries across all tables. This allows us to register
models inheriting from the `AbstractFileModel` without the need of **django-polymorphic**, and thus
a join between two or more tables for each query.

Multiple root folder are allowed. They can be used side by side in the Django admin and are listed
in the sidebar. For each root folder, a different Django storage can be configured. It also is
possible to restrict a root folder to a Site and/or to an AdminSite.

The Admin interface has also been completely rewritten. For instance, there is no more list view for
the `FolderModel` and the `FileModel` (or any specialized implementation). Instead, there are only
details views for each of those models. This is much nearer to what a user would expect from a file
system. Therefore, if a user wants to access the list view of a folder, he is redirected immediately
to the detail view of the root folder of the given tenant. From there, he can traverse the folder
tree in the same manner he's used to from his operating system.


## New User Interface

The user interface has also been completely rewritten. It offers drag and drop functionality for
moving files and folders. It now is possible to select multiple files and folders at once by a
rectangular selection with the mouse.
Double-clicking on a folder opens it, by loading the detail view for that `FolderModel`. Selected
files or folders can be dragged into a target folder. They can also be cutted or copied to a
clipboard and pasted into another folder.


### Trash Folder

Each user now has its *own private trash* folder. Whenever he deletes a file or folder, it is moved
to that trash folder. From there, he can restore the file or folder, or delete it permanently. The
trash folder can be emptied automatically after a given time period.


## Permission System

The permission system of **django-filer** is using the concept of Access Control Lists (ACLs)
similar to Posix or NTFS ACLs. This allows granting fine-grained permissions to everybody,
individual users and/or groups for each file and folder.

Permissions are controlled through the model named `AccessControlEntry`. This model has a foreign
key onto `InodeModel` and a so-called "principal". A principal is either a user, a group or for
everyone. They are mutually exclusive and implemented as a nullable foreign key onto `User`, or a
foreign key onto `Group`. Either of them can be set, but not both. If neither is set, the permission
is considered for everyone.

By using a separate model `AccessControlEntry`, **django-filer** can now compute the permissions
using just one database (sub-)query while filtering all inodes. Until version 3, the permissions had
to be computed traversing all ancestors starting from the current folder up to the root of the
folder tree. This was a time-consuming operation and made **django-filer** slow for large datasets.

Each `AccessControlEntry` has a bitmap field used to represent:
* `write` set for a folder: Allows the user to upload a file, to change the name of that folder,
  to reorder files in that folder, to move files out of that filer.
* `write` set for a file: Allows the user to replace a file, to edit the file's meta-data, and to
  move the file to another folder, if the source and target folders have write permissions.
* `read` set for a folder: Allows the user to open that folder and view its content.
* `read` set for a file: Allows the user to view a thumbnail of that file inside its containing
  folder and use that file, including copying.
* `admin`: Allows the user to change the permissions of that folder or file.
* A generic foreign key pointing onto the `InodeModel`. This creates a one-to-many relation between
  different file types and folders on one side and the access control list on the other.

In addition to `AccessControlEntry` the permission system also provides a model named
`DefaultAccessControlEntry`. This acts as a template for newly  which is used to set default permissions for files and folders created as children of a specific folder. This allows to set a permission template for each folder, which is inherited by all files and folders created as children of that folder. This is implemented as a separate model with a foreign key onto the `FolderModel`, because it is not possible to use the same model for both purposes, since the default permissions must be inherited by all children of a folder, while the regular permissions only apply to the file or folder they are attached to.

*
* A foreign key onto the folder model to set a permission template. Read below for details.
* The `execute` flag as seen in Unix file systems and other ACL implementations does not make sense
  in this context and is not implemented.

If a folder has `write` but no `read` permission, the user can upload files into that folder, but
doesn't see files from other users. This is named "Dropbox" functionality.

Each file and folder has a foreign key named `owner`, pointing onto the `User` model. The owner of a
file or folder can change its permissions if he has the global permission to do so. When creating a
new file or folder, the currently loggedin user is set as the owner of that file or folder.

Only a superuser and the owner of a file or folder can change its permissions. The superuser can
change the permissions of any file or folder. Staff users can change the permissions only of files
they own themselves.

Only a superuser can change the owner of a file or folder.

In addition to the file and folder permissions, each folder requires a template of permissions on how to
inherit them to files and folders created as children of that specific folder. This can be achieved with
a separate foreign key in model `AccessControlEntry` pointing onto the `FolderModel`.

Microsoft gives a good explanation on the implementation of
[ACLs in their Data-Lake implementation](https://learn.microsoft.com/en-us/azure/storage/blobs/data-lake-storage-access-control).


### Alternative Views

The user interface offers four alternative views for the folder tree.

**Tiles** is a "flat" view, which shows all files and folders as a bunch of tiles.

**Mosaic** is very similar to the "Tiles" view, but shows a much smaller version of those file,
folder and image icons.

**List** is a view with detailed information about every file or folder. Here every item requires a
separate row.

**Column** is a view which shows columns for the currently selected folder and each of its
ancestors. This allows to easily move files between those folders.


### Multiple Favrourite Folders

Each user can have multiple favourite folders. This allows him to quickly access those folders from
the navigation bar. It is also possible to drag a file from the current view into one of the tabs
for of the favorite folders.


### Implementation Details

The new user interface is based on the [React](https://reactjs.org/) framework with the
[DnD-Kit](https://docs.dndkit.com/) as its main additional dependency.


## Installation

The new version of **django-filer** is not yet available on PyPI. Therefore, you have to install it
from GitHub:

```shell
git clone https://github.com/django-cms/django-filer.git
cd django-filer
git switch finder
pip install --no-deps -e .
```

The new version of **django-filer** requires Django-5.2 or later.

The new version of **django-filer** currently has only been tested with SQLite and Postgres, but
should also work on MariaDB and MySQL.

In `settings.py` of your project, add these extra dependencies or those you really need:

```python
    INSTALLED_APPS = [
        ...
        'finder',
        'finder.contrib.archive',  # supports zip, tar, tar.gz, tar.bz2, tar.xz
        'finder.contrib.audio',  # supports mp3, ogg, flac, wav
        'finder.contrib.common',  # supports PDF, spreadsheets
        'finder.contrib.image.pil',  # supports bmp, gif, jpeg, png, tiff
        'finder.contrib.image.svg',  # supports svg
        'finder.contrib.video',  # supports mp4, webm, ogv
        ...
    ]
```

If you use:
* `finder.contrib.audio` or `finder.contrib.video`, assure that `ffmpeg-python` is installed.
* `finder.contrib.image.pil`, assure that `Pillow` is installed.
* `finder.contrib.image.svg`, assure that `reportlab` and `svglib` are installed.
* Postgres as a database, install `psycopg2` or `psycopg2-binary` if available for your platform.

Each root folder requires two storage backends. One for the public files and one for their
thumbnails and/or samples. Add these storage backends to the `STORAGES` setting in your
`settings.py`:

```python
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
    'finder_public': {
        'BACKEND': 'finder.storage.FinderSystemStorage',
        'OPTIONS': {
            'location': '/path/to/your/media/filer_public',
            'base_url': '/media/filer_public/',
            'allow_overwrite': True,
        },
    },
    'finder_public_samples': {
        'BACKEND': 'finder.storage.FinderSystemStorage',
        'OPTIONS': {
            'location': '/path/to/your/media/filer_public_thumbnails',
            'base_url': '/media/filer_public_thumbnails/',
            'allow_overwrite': True,
        },
    },
}
```

If instead of using the local file system you want to use another storage backend, such as MinIO,
Amazon S3 or Google Cloud Storage, configure the corresponding storage backend in the `STORAGES`
setting as:

```python
STORAGES = {
    ...
    'finder_public': {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {...},
    },
    'finder_public_samples': {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {...},
    },
}
```

Note that multiple root folders can share the same storage location or bucket.

Run the migrations for app `finder`:

```shell
python manage.py migrate finder
```

Create a root folder using the above configuration:

```shell
python manage.py finder add-root public --values name="Public Folder" storage=finder_public sample_storage=finder_public_samples
```

You can create multiple root folders, each with their own unique slug and name. You may configure a
storage backend for each root folder or share them between multiple root folders.

If you already have **django-filer** installed and that database is filled, you can migrate the
meta-data of those files and folders into the new database tables. The physical files on disk are
not affected by this migration. Remember to leave the `filer` app in `INSTALLED_APPS`.

```shell
python manage.py filer_to_finder
```

This does not affect the original database tables. You can still use the original **django-filer**
codebase in parallel to the new "Finder" branch. They both share the same underlying file system,
usually `media/filer_public` but store their meta information in completely independent database
tables. The only caveat is that you should not erase files in the trash folder, because then they
are also gone on disk.

The client part of the new admin user must be compiled before it can be used. This requires a modern
version (18 or later) of [Node.js](https://nodejs.org/en/) and [npm](https://www.npmjs.com/), which usually are installed anyway.
The following commands installs the requirements and compiles the code:

```shell
cd django-filer
npm install --include=dev
npm run buildall
```


## Usage

After restarting the development server, you can access the new admin user interface at the URL
http://localhost:8000/admin/finder/foldermodel/ . Clicking on that link will redirect you to the
root folder of the current site.


## Admin Backend

The admin backend is implemented as a web interface mimicking the features of the Finder app of your
operating system's graphical user interface. It is possible to …

* Download, upload files and to view them as thumbnailed images.
* Navigate through the folder tree by double-clicking on a folder.
* Move files and folders by drag and drop.
* Select multiple files and folders by a rectangular selection with the mouse.
* Cut or copy files and folders to a clipboard and paste them into another folder.
* Delete files and folders, which are moved to a trash folder.
* Restore files and folders from the trash folder or to delete them permanently.
* Create new folders and to upload files.
* Rename files and folders by slowly double-clicking on their name.
* Create multiple tabs for favourite folders quick access. They also can be used to drag files from
  the current view into one of the tabs.
* Search for files and folders.
* Tag files and filter them by their tags.


## Interface to other Django projects

**django-filer** (Finder branch) ships with a new file selection field. This field can be used in
any Django model. It allows to select a file from the files stored inside **django-filer**. It also
allows to upload a local file and use it immediatly.

Example:

```python
from django.db import models
from finder.models.fields import FinderFileField

class MyModel(models.Model):
    my_file = FinderFileField(
        null=True,
        blank=True,
    )
```

Forms generated from this model will have a file selection widget for the `my_file` field. When
rendered as HTML, this widget becomes the webcomponent `<finder-file-select …></finder-file-select>`
with a few additional attributes. The JavaScript part of the widget must be included using the
script tag `<script src="{% static 'finder/js/finder-select.js' %}"></script>`.

The demonstration app provides an example how this field can be used in a form. Just vist the URL
http://localhost:8000/demoapp/ and click on the blank area to either select an existing file or
upload a new one.


## Thumbnailing

In addition to the x- and y-coordinates of the focal point, the `ImageModel` now also stores the
main area of interest as a square. This information then is used to create thumbnails using
[Art Direction](https://www.smashingmagazine.com/2016/01/responsive-image-breakpoints-generation/).

The method `finder.contrib.image.pil.models.ImageModel.crop()` creates a thumbnail of the given
image taking the focal point and the resolution into account. The following rules apply when
cropping and thumbnailing an image:

* The thumbnailed image always contains at least the main area of interrest, except for this
  situation: If the thumbnail is narrower than the main area of interest, the thumbnail will be
  cropped to the center of that area.
* The resolution of the area to be thumbnailed is always at least the same as the resolution of the
  original image.


will take the resolution of the corresponsding image into
consideration. This will allow to create different versions of the same canonical image, depending
on the width of the device the image is displayed.

By extending the focal point to three degrees of freedom, it is possible to create a thumbnail
taking the resolution into account. This allows us to create thumbnails taking art direction into
consideration. For instance, if a user uploads a portrait image, the focal point can be set to the
head of the person in that image.


## Further Steps

* A permission system based on the idea of Access Control Lists, see above.
* A quota system, which allows to limit the amount of disk space a user can use.
* Thumbnailing, see above.


## Further Readings

https://developer.mozilla.org/en-US/docs/Web/HTML/Guides/Responsive_images
https://www.smashingmagazine.com/2014/05/responsive-images-done-right-guide-picture-srcset/
https://www.smashingmagazine.com/2016/01/responsive-image-breakpoints-generation/
https://www.smashingmagazine.com/2016/09/automating-art-direction-with-the-responsive-image-breakpoints-generator/
https://cloudfour.com/thinks/responsive-images-101-part-9-image-breakpoints/
https://cloudfour.com/thinks/sensible-jumps-in-responsive-image-file-sizes/

https://cloudfour.com/thinks/the-real-conflict-behind-picture-and-srcset/

## License

This part of the code will be licensed under the terms of the [MIT License](https://opensource.org/licenses/MIT).
