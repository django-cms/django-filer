.. _extending_filer:

Extending Django Filer
======================

Django Filer ships with support for image files, and generic files (everything
that's not an image).

So what if you wanted to add support for a particular kind of file thats's not already included?
It's easy to extend it to do this, without needing to touch the Filer's code at all
(and no-one wants to have to maintain fork if they can avoid it).

So for example, you might want to be able to manage video files. You could of
course simply store and file them as generic file types, but that might not be
enough - perhaps your own application needs to know that certain files are in
fact video files, so that it can treat them appropriately (process them, allow
only them to be selected in certain widgets, and so on).

In this example we will create support for video files.

The model
---------

The very basics
...............

In your own application, you need to create a Video model. This model has to inherit from :py:class:`filer.models.filemodels.File`.

.. code-block:: python

    # import the File class to inherit from
    from filer.models.filemodels import File
    
    # we'll need to refer to filer settings
    from filer import settings as filer_settings
    
    class Video(File):
        pass # for now...
    

When a file is uploaded, :py:meth:`filer.admin.clipboardadmin.ClipboardAdmin.ajax_upload` loops over the different classes in ``filer.settings.FILER_FILE_MODELS`` and calls its ``matches_file_type()`` to see if the file matches a known filename extension.

When a match is found, the filer will create an instance of that class for the file.

So let's add a ``matches_file_type()`` method to the ``Video`` model:

.. code-block:: python

    @classmethod
    def matches_file_type(cls, iname, ifile, request):
        # the extensions we'll recognise for this file type
        filename_extensions = ['.dv', '.mov', '.mp4', '.avi', '.wmv',]
        ext = os.path.splitext(iname)[1].lower()
        return ext in filename_extensions

Now you can upload files of those types into the Filer. 

For each one you upload an instance of your ``Video`` class will be created.


Icons
.....

At the moment, the files you upload will have the Filer's generic file icon - not very appropriate or helpful for video. What you need to do is add a suitable ``_icon`` attribute to the class.

The :py:class:`filer.models.filemodels.File` class we've inherited from has an ``icons()`` property, from :py:class:`filer.models.mixins.IconsMixin`. 

This checks for the ``_icon`` attribute; if it finds one, it uses it to build URLs for the icons in various different sizes. If ``_icons`` is ``video``, a typical result might be ``/static/filer/icons/video_48x48.png``.

Of course, you can also create an ``icons()`` property specific to your new model. For example, :py:class:`filer.models.imagemodels.Image` does that, so that it can create thumbnail icons for each file rather than a single icon for all of that type.

In our ``Video`` model the simple case will do: 

.. code-block:: python

        # the icon it will use
        _icon = "video"

And in fact, the Filer *already* has an icon that matches this - if there were not already a set of video icons in the Filer's static assets, we'd have to provide them - see ``filer/static/icons`` for examples.

The admin
---------

Now we need to register our new model with the admin. Again, the very simplest case:

.. code-block:: python

    from django.contrib import admin
    from filer.admin.fileadmin import FileAdmin
    from models import Video

    admin.site.register(Video, FileAdmin) # use the standard FileAdmin 

... but of course if your model had particular fields of its own (as for example the ``Image`` model has a ``subject_location`` field) you would create your own ModelAdmin class for it, along with a form, special widgets and whatever else you needed.

Using your new file type
------------------------

You've now done enough to be able to get hold of files of your new kind in the admin (wherever the admin uses a ``FilerFileField``) but to make it really useful we need to to a little more.

For example, it might be useful to have:

* its own field type to get hold of it in some other model
* a special form for the field
* a widget for selecting it in the admin
* ... and so on

How you use it will be up to you, but a fairly typical use case would be in a django CMS plugin, and that is the example that will be followed here.

Create a custom field for your file type
----------------------------------------

.. code-block:: python

    from filer.fields.file import FilerFileField
    
    class FilerVideoField(FilerFileField):
        default_model_class = Video

Of course you could also create an admin widget and admin form, but it's not necessary at this stage - the ones generic files use will do just fine.


Create some other model that uses it
------------------------------------

Here, it's going to be a django CMS plugin:

.. code-block:: python

    from cms.models import CMSPlugin
    
    class VideoPluginEditor(CMSPlugin):
        video = FilerVideoField()
        # you'd probably want some other fields in practice...

You'll have to provide an admin class for your model; in this case, the admin will be provided as part of the django CMS plugin architecture.

.. note::

    If you are not already familiar with the django CMS plugin architecture, http://docs.django-cms.org/en/latest/extending_cms/custom_plugins.html#overview will provide an explanation.

.. code-block:: python

    from cms.plugin_base import CMSPluginBase
    from models import VideoPluginEditor
    
    class VideoPluginPublisher(CMSPluginBase):
        model = VideoPluginEditor
        render_template = "video/video.html"
        text_enabled = True
        admin_preview = False

        def icon_src(self, instance):
            return "/static/plugin_icons/video.png"

        def render(self, context, instance, placeholder):
            context.update({
                'video':instance,
                'placeholder':placeholder,
            })
            return context

    plugin_pool.register_plugin(VideoPluginPublisher)

... and now, assuming you have created a suitable ``video/video.html``, you've got a working plugin that will make use of your new Filer file type.  

Other things you could add
--------------------------

Admin templating
................

``filer/templates/templates/admin/filer/folder`` lists the individual items in each folder.
It checks ``item.file_type`` to determine how to display those items and what to display for them.

You might want to extend this, so that the list includes the appropriate information for your new file type.
In that case you will need to override the template, and in the ``Video`` model:

.. code-block:: python

        # declare the file_type for the list template
        file_type = 'Video'
        
Note that if you do this, you *will* need to override the template - otherwise your items will fail to display in the folder lists.

Overriding the Directory Listing Search
---------------------------------------

By default, filer will search against ``name`` for :py:class:`Folders
<filer.models.foldermodels.Folder>` and ``name``, ``description``, and
``original_filename`` for :py:class:`Files <filer.models.filemodels.File>`, in
addition to searching against the owner.  If you are using ``auth.User`` as
your User model, filer will search against the ``username``, ``first_name``,
``last_name``, ``email`` fields.  If you are using a custom User model, filer
will search against all fields that are CharFields except for the password
field.  You can override this behavior by subclassing the
:py:class:`filer.admin.folderadmin.FolderAdmin` class and overriding the
:py:attr:`~filer.admin.FolderAdmin.owner_search_fields` property.

.. code-block:: python

    # in an admin.py file
    from django.contrib import admin
    from filer.admin import FolderAdmin
    from filer.models import Folder

    class MyFolderAdmin(FolderAdmin):
        owner_search_fields = ['field1', 'field2']

    admin.site.unregister(Folder)
    admin.site.register(Folder, FolderAdmin)

You can also override the search behavior for :py:class:`Folders<filer.models.foldermodels.Folder>`.
Just override :py:attr:`~filer.admin.folderadmin.FolderAdmin.search_fields` by subclassing
the :py:class:`filer.admin.folderadmin.FolderAdmin`. It works as described in
`Django's docs <https://docs.djangoproject.com/en/1.8/ref/contrib/admin/#django.contrib.admin.ModelAdmin.search_fields>`_. E.g.:


.. code-block:: python

    # in an admin.py file
    class MyFolderAdmin(FolderAdmin):
        search_fields = ['=field1', '^field2']

    admin.site.unregister(Folder)
    admin.site.register(Folder, MyFolderAdmin)

Providing custom Image model
----------------------------

As the ``Image`` model is special, a different way to implement custom Image model is required.

Defining the model
..................

First a custom model must be defined; it should inherit from BaseImage, the basic abstract class:

.. code-block:: python

    from filer.models.abstract.BaseImage

    class CustomImage(BaseImage):
        my_field = models.CharField(max_length=10)

        class Meta:
            # You must define a meta with en explicit app_label
            app_label = 'myapp'

The model can be defined in any installed application declared **after** ``django-filer``.

``BaseImage`` defines the following fields (plus the basic fields defined in ``File``):

 * default_alt_text
 * default_caption
 * subject_location

you may add whatever fields you need, just like any other model.

..warning: ``app_label`` in ``Meta`` must be explicitly defined.


Customize the admin
...................

If you added fields in your custom Image model, you have to customize the admin too:


.. code-block:: python

    from django.contrib import admin
    from filer.admin.imageadmin import ImageAdmin
    from filer.models.imagemodels import Image

    class CustomImageAdmin(ImageAdmin):
        # your custom code
        pass

    # Using build_fieldsets allows to easily integrate common field in the admin
    # Don't define fieldsets in the ModelAdmin above and add the custom fields
    # to the ``extra_main_fields`` or ``extra_fieldsets`` as shown below
    CustomImageAdmin.fieldsets = CustomImageAdmin.build_fieldsets(
        extra_main_fields=('default_alt_text', 'default_caption', 'my_field'...),
        extra_fieldsets=(
            ('Subject Location', {
                'fields': ('subject_location',),
                'classes': ('collapse',),
            }),
        )
    )

    # Unregister the default admin
    admin.site.unregister(ImageAdmin)
    # Register your own
    admin.site.register(Image, CustomImageAdmin)

Swap the Image model
....................

Set ``FILER_IMAGE_MODEL`` to the dotted path of your custom model:


.. code-block:: python

    FILER_IMAGE_MODEL = 'my.app.models.CustomImage'
