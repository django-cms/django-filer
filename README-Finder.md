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

The client part of the new admin user interface has no runtime dependencies. It is compiled into a
single JavaScript file, which is included by the corresponding admin views.


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

In `settings.py` of your project, add these extra dependencies or those one you really need:

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

If you use `finder.contrib.audio`, assure that `pydub` is installed.
If you use `finder.contrib.image.pil`, assure that `Pillow` is installed.
If you use `finder.contrib.image.svg`, assure that `reportlab` and `svglib` are installed.
If you use `finder.contrib.video`, assure that `ffmpeg-python` is installed.


Run the migrations for app `finder`:

```shell
python manage.py migrate finder
```

If you already have **django-filer** installed and that database is filled, you can migrate the
meta-data of those files and folders into the new database tables. The pysical files on disk are not
affected by this migration.

```shell
python manage.py filer_to_finder
```

This does not affect the original database tables. You can still use the original **django-filer**
codebase in parallel to the new "Finder" branch. They both share the same underlying file system,
usually `media/filer_public` but store their meta information in completely independent database
tables. The only cavat is that you should not erase files in the trash folder, because then they are
also gone on disk.

The client part of the new admin user must be compiled before it can be used. This requires a modern
version (18 or later) of [Node.js](https://nodejs.org/en/) and [npm](https://www.npmjs.com/), which usually are installed anyway.
The following commands install the requirements all compiles the code:

```shell
cd django-filer
npm install --include=dev
npm run buildall
```


## Usage

After restarting the development server, you can access the new admin user interface at the URL
http://localhost:8000/admin/finder/foldermodel/ . Clicking on that link will redirect you to the
root folder of the current site.


## Limitations

Currently only the admin backend is implemented. I am currently working on a file selection widget
which can be used in any frontend or backend application.


## Further Steps

The focal point of the `ImageModel` will take the resolution of the corresponsding image into
consideration. This will allow to create different versions of the same canonical image, depending
on the width of the device the image is displayed.

The permission system will also be implemented using a different model. This probaly will orient
itself on the Access Control Lists (ACLs) of [NTFS](https://learn.microsoft.com/en-us/windows/win32/secauthz/access-control-lists).
This will allow to grant permissions to users and groups for each folder (but not file) individually.

A quota system will be implemented, which allows to limit the amount of disk space a user can use.


## License

This part of the code will be licensed under the terms of the [MIT License](https://opensource.org/licenses/MIT).
