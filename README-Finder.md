# Django-Filer ("Finder" branch)

The "Finder" branch of django-filer is a complete rewrite of the original **django-filer** project.
It is a work in progress and is not yet ready for production use. However, the code is in a state
where it can be used for testing and development purposes.

A rewrite was necessary because the original codebase was not maintainable anymore. Please read this
[discussion](https://github.com/django-cms/django-filer/discussions/1348) for details on why a rewrite was necessary.

Apart from the maintainability issues, using the File and Folder models was not possible in a
multi-tenant environment. Extending the file model with a more specialized implementation was
possible in theory, but so complicated that apart from the `ImageModel` no other implementations
ever have been created.


## Less third-party dependencies

The "Finder" branch of django-filer has less third-party dependencies. It does not depend on
[django-polymorphic](https://django-polymorphic.readthedocs.io/en/stable/),
[django-mptt](https://django-mptt.readthedocs.io/en/latest/) and
[easy-thumbnails](https://easy-thumbnails.readthedocs.io/en/latest/) anymore.

For large datasets [django-cte](https://github.com/dimagi/django-cte) is reccomended, in order to improve the speed when searching.

The client part of the new admin user interface has no runtime dependencies. It is compiled into two
JavaScript files, which are included by the corresponding admin views. One of them is used for the
django-admin interface, the other one for the frontend. The frontend part is also used for the new
file selection widget.


## Extensibility

The "Finder" branch of django-filer is designed to be extensible for every MIME-type one desires.
Therefore, those extensions might need their own dependencies in order to extract or visualize a
certain type of file. A "vanilla" installation can only distinguish between files and folders.


## New Model Features

The "Finder" branch introduces a new model named `InodeModel`. This is the base class for all other
models, such as the `FileModel`, the `FolderModel` and all other specialized implementations. By
using a UUID instead of a numerical primary key, it is possible to use different database tables
while preserving the possibility to perform queries across all tables. This allows us to register
models inheriting from the `AbstractFileModel` without the need of **django-polymorphic**, and thus
a join between two or more tables for each query.

The Admin interface has also been completely rewritten and allows multi-tenant usage out of the box.
For instance, there is no more list view for the `FolderModel` and the `FileModel` (or any
specialized implementation). Instead, there are only details views for each of those models. This is
much nearer to what a user would expect from a file system. Therefore, if a user wants to access the
list view of a folder, he is redirected immediately to the detail view of the root folder of the
given tenant. From there, he can traverse the folder tree in the same manner he's used to from his
operating system.


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
the navigation bar. It also it pssoble to drag a file from the current view into one of the tabs for
of the favorite folders.


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

The new version of **django-filer** requires Django-5.2 or later. Since this currently is not
released, you have to install the current development version of Django from GitHub as well.

The new version of **django-filer** currently has only been tested with SQLite and Postgres, but
should also work on MariaDB and MySQL.

In `settings.py` of your project, add these extra dependencies or those you really need:

```python
    INSTALLED_APPS = [
        ...
        'finder',
        'finder.contrib.archive',  # supports zip, tar, tar.gz, tar.bz2, tar.xz
        'finder.contrib.audio',  # supports mp3, ogg, flac, wav
        'finder.contrib.common',  # supports pdf, spreadsheets
        'finder.contrib.image.pil',  # supports bmp, gif, jpeg, png, tiff
        'finder.contrib.image.svg',  # supports svg
        'finder.contrib.video',  # supports mp4, webm, ogv
        ...
    ]
```

If you use:
* `finder.contrib.audio`, assure that `ffmpeg-python` is installed.
* `finder.contrib.image.pil`, assure that `Pillow` is installed.
* `finder.contrib.image.svg`, assure that `reportlab` and `svglib` are installed.
* `finder.contrib.video`, assure that `ffmpeg-python` is installed.
* Postgres as database, install `psycopg2` or `psycopg2-binary` if available for your platform.

Run the migrations for app `finder`:

```shell
python manage.py migrate finder
```

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

The testapp provides an example how this field can be used in a form. Just vist the URL
http://localhost:8000/admin/finder/foldermodel/ and click on the blank area to either select an
existing file or upload a  new one.


## Further Steps

The focal point of the `ImageModel` will take the resolution of the corresponsding image into
consideration. This will allow to create different versions of the same canonical image, depending
on the width of the device the image is displayed.

The permission system will be implemented using a model based on the idea of Access Control Lists
(ACLs) of [NTFS](https://learn.microsoft.com/en-us/windows/win32/secauthz/access-control-lists). This will allow to grant permissions to users and groups for each folder
(but not file) individually.

A quota system will be implemented, which allows to limit the amount of disk space a user can use.


## License

This part of the code will be licensed under the terms of the [MIT License](https://opensource.org/licenses/MIT).
