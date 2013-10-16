#-*- coding: utf-8 -*-
from django.contrib.auth import models as auth_models
from django.core import urlresolvers
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.db import (models, IntegrityError, transaction)
from django.utils.translation import ugettext_lazy as _
from filer.fields.multistorage_file import MultiStorageFileField
from filer.models import mixins
from filer.models.foldermodels import Folder
from filer.utils.cms_roles import *
from filer import settings as filer_settings
from django.db.models import Count
import polymorphic
import hashlib
import os


class FilesChainableQuerySet(object):

    def readonly(self):
        return self.filter(folder__folder_type=Folder.CORE_FOLDER)

    def find_duplicates(self, file_obj):
        return self.exclude(pk=file_obj.pk).filter(sha1=file_obj.sha1)

    def restricted(self, user):
        sites = get_sites_without_restriction_perm(user)
        if not sites:
            return self.none()
        return self.filter(
            restricted=True,
            folder__site__in=sites)

    def unrestricted(self, user):
        sites = get_sites_without_restriction_perm(user)
        if not sites:
            return self
        return self.exclude(
            restricted=True,
            folder__site__in=sites)


class EmptyFilesQS(models.query.EmptyQuerySet, FilesChainableQuerySet):
    pass


class FileQuerySet(polymorphic.query.PolymorphicQuerySet,
                   FilesChainableQuerySet):
    pass


class FileManager(polymorphic.PolymorphicManager):

    def get_query_set(self):
        return FileQuerySet(self.model, using=self._db)

    def get_empty_query_set(self):
        return EmptyFilesQS(self.model, using=self._db)

    def find_all_duplicates(self):
        return {file_data['sha1']: file_data['count']
                for file_data in File.objects.values('sha1').annotate(
                    count=Count('id')).filter(count__gt=1)}


class File(polymorphic.PolymorphicModel, mixins.IconsMixin):
    file_type = 'File'
    _icon = "file"
    folder = models.ForeignKey(Folder, verbose_name=_('folder'), related_name='all_files',
        null=True, blank=True)
    file = MultiStorageFileField(_('file'), null=True, blank=True, db_index=True, max_length=255)
    _file_size = models.IntegerField(_('file size'), null=True, blank=True)

    sha1 = models.CharField(_('sha1'), max_length=40, blank=True, default='')

    has_all_mandatory_data = models.BooleanField(_('has all mandatory data'), default=False, editable=False)

    original_filename = models.CharField(_('original filename'), max_length=255, blank=True, null=True)
    name = models.CharField(max_length=255, null=True, blank=True,
        verbose_name=_('name'))
    description = models.TextField(null=True, blank=True,
        verbose_name=_('description'))

    owner = models.ForeignKey(auth_models.User,
        related_name='owned_%(class)ss',
        null=True, blank=True, verbose_name=_('owner'))

    uploaded_at = models.DateTimeField(_('uploaded at'), auto_now_add=True)
    modified_at = models.DateTimeField(_('modified at'), auto_now=True)

    is_public = models.BooleanField(
        default=filer_settings.FILER_IS_PUBLIC_DEFAULT,
        verbose_name=_('Permissions disabled'),
        help_text=_('Disable any permission checking for this ' +\
                    'file. File will be publicly accessible ' +\
                    'to anyone.'))

    restricted = models.BooleanField(
        _("Restrict Editors and Writers from being able to edit "
          "or delete this asset"), default=False,
        help_text=_('If this box is checked, '
                    'Editors and Writers will still be able to '
                    'view the asset, add it to a plugin or smart '
                    'snippet but will not be able to delete or '
                    'modify the current version of the asset.'))

    objects = FileManager()

    @classmethod
    def matches_file_type(cls, iname, ifile, request):
        return True  # I match all files...

    def __init__(self, *args, **kwargs):
        super(File, self).__init__(*args, **kwargs)
        self._old_is_public = self.is_public
        self._old_name = self.name
        self._old_folder = self.folder
        self._force_commit = False

    def clean(self):
        if self.folder:
            entries = self.folder.entries_with_names([self.actual_name])
            if entries and any(entry.pk != self.pk for entry in entries):
                raise ValidationError(
                    _(u'Current folder already contains a file named %s') % \
                        self.actual_name)

    def _move_file(self):
        """
        Move the file from src to dst.
        """
        src_file_name = self.file.name
        dst_file_name = self._meta.get_field('file').generate_filename(
            self, self.original_filename)

        if self.is_public:
            src_storage = self.file.storages['private']
            dst_storage = self.file.storages['public']
        else:
            src_storage = self.file.storages['public']
            dst_storage = self.file.storages['private']

        # delete the thumbnail
        # We are toggling the is_public to make sure that easy_thumbnails can
        # delete the thumbnails
        self.is_public = not self.is_public
        self.file.delete_thumbnails()
        self.is_public = not self.is_public
        # This is needed because most of the remote File Storage backend do not
        # open the file.
        src_file = src_storage.open(src_file_name)
        src_file.open()
        self.file = dst_storage.save(dst_file_name,
            ContentFile(src_file.read()))
        src_storage.delete(src_file_name)

    def _copy_file(self, destination, overwrite=False):
        """
        Copies the file to a destination files and returns it.
        """

        if overwrite:
            # If the destination file already exists default storage backend
            # does not overwrite it but generates another filename.
            # TODO: Find a way to override this behavior.
            raise NotImplementedError

        src_file_name = self.file.name
        storage = self.file.storages['public' if self.is_public else 'private']

        if hasattr(storage, 'copy'):
            storage.copy(src_file_name, destination)
            return destination
        else:
            # This is needed because most of the remote File Storage backend do not
            # open the file.
            src_file = storage.open(src_file_name)
            src_file.open()
            return storage.save(destination, ContentFile(src_file.read()))

    def generate_sha1(self):
        sha = hashlib.sha1()
        self.file.seek(0)
        sha.update(self.file.read())
        self.sha1 = sha.hexdigest()
        # to make sure later operations can read the whole file
        self.file.seek(0)

    def set_restricted_from_folder(self):
        if self.folder and self.folder.restricted:
            self.restricted = self.folder.restricted

    def save(self, *args, **kwargs):
        self.set_restricted_from_folder()
        # check if this is a subclass of "File" or not and set
        # _file_type_plugin_name
        if self.__class__ == File:
            # what should we do now?
            # maybe this has a subclass, but is being saved as a File instance
            # anyway. do we need to go check all possible subclasses?
            pass
        elif issubclass(self.__class__, File):
            self._file_type_plugin_name = self.__class__.__name__
        # cache the file size
        # TODO: only do this if needed (depending on the storage backend the whole file will be downloaded)
        try:
            self._file_size = self.file.size
        except:
            pass
        if self._old_is_public != self.is_public and self.pk:
            self._move_file()
            self._old_is_public = self.is_public

        # generate SHA1 hash
        # TODO: only do this if needed (depending on the storage backend the whole file will be downloaded)
        try:
            self.generate_sha1()
        except Exception, e:
            pass
        if filer_settings.FOLDER_AFFECTS_URL and \
                (self._is_name_chnaged() or
                 self._old_folder != self.folder):
            self._force_commit = True
            self.update_location_on_storage(*args, **kwargs)
        else:
            super(File, self).save(*args, **kwargs)

    save.alters_data = True

    def _is_name_chnaged(self):
        if self._old_name in ('', None):
            return self.name not in ('', None)
        else:
            return self._old_name != self.name

    def _delete_thumbnails(self):
        source = self.file.get_source_cache()
        if source:
            self.file.delete_thumbnails()
            source.delete()

    def update_location_on_storage(self, *args, **kwargs):
        old_location = self.file.name
        # thumbnails might get physically deleted evenif the transaction fails
        # though luck... they get re-created anyway...
        self._delete_thumbnails()
        new_location = self.file.field.upload_to(self, self.actual_name)
        storage = self.file.storage

        def copy_and_save():
            saved_as = self._copy_file(new_location)
            assert saved_as == new_location, '%s %s' % (saved_as, new_location)
            self.file = saved_as
            super(File, self).save(*args, **kwargs)

        if self._force_commit:
            with transaction.commit_manually():
                # The manual transaction management here breaks the transaction management
                # from django.contrib.admin.options.ModelAdmin.change_view
                # This isn't a big problem because the only CRUD operation done afterwards
                # is an insertion in django_admin_log. If this method rollbacks the transaction
                # then we will have an entry in the admin log describing an action
                # that didn't actually finish succesfull.
                # This 'hack' can be removed once django adds support for on_commit and
                # on_rollback hooks (see: https://code.djangoproject.com/ticket/14051)
                try:
                    copy_and_save()
                except Exception:
                    try:
                        transaction.rollback()
                    finally:
                        # delete the file from new_location if the db update failed
                        if old_location != new_location:
                            storage.delete(new_location)
                    raise
                else:
                    transaction.commit()
                    # only delete the file on the old_location if all went OK
                    if old_location != new_location:
                        storage.delete(old_location)
        else:
            copy_and_save()
        return new_location

    def delete(self, *args, **kwargs):
        # Delete the model before the file
        super(File, self).delete(*args, **kwargs)
        # Delete the file if there are no other Files referencing it.
        if not File.objects.filter(file=self.file.name,
                                   is_public=self.is_public).exists():
            self.file.delete(False)
    delete.alters_data = True

    @property
    def label(self):
        if self.name in ['', None]:
            text = self.original_filename or 'unnamed file'
        else:
            text = self.name
        text = u"%s" % (text,)
        return text

    def __lt__(self, other):
        return cmp(self.label.lower(), other.label.lower()) < 0

    @property
    def actual_name(self):
        """The name displayed to the user.
        Uses self.name if set, otherwise it falls back on self.original_filename.

        This property is used for enforcing unique filenames within the same fodler.
        """
        if self.name in ('', None):
            actual_name = u"%s" % (self.original_filename,)
        else:
            actual_name = u"%s" % (self.name,)
        return actual_name

    @property
    def pretty_logical_path(self):
        its_dir = self.logical_folder
        if its_dir.is_root:
            directory_path = u''
        else:
            directory_path = its_dir.pretty_logical_path
        full_path = u'{}{}{}'.format(directory_path, os.sep, self.actual_name)
        return full_path

    def __unicode__(self):
        return self.actual_name

    def get_admin_url_path(self):
        return urlresolvers.reverse(
            'admin:%s_%s_change' % (self._meta.app_label,
                                    self._meta.module_name,),
            args=(self.pk,)
        )

    @property
    def file_ptr(self):
        """
        Evil hack to get around the cascade delete problem with django_polymorphic.
        Prevents ``AttributeError: 'File' object has no attribute 'file_ptr'``.
        This is only a workaround for one level of subclassing. The hierarchy of
        object in the admin delete view is wrong, but at least it works.
        """
        return self

    @property
    def url(self):
        """
        to make the model behave like a file field
        """
        try:
            r = self.file.url
        except:
            r = ''
        return r

    @property
    def path(self):
        try:
            return self.file.path
        except:
            return ""

    @property
    def size(self):
        return self._file_size or 0

    @property
    def extension(self):
        filetype = os.path.splitext(self.file.name)[1].lower()
        if len(filetype) > 0:
            filetype = filetype[1:]
        return filetype

    @property
    def logical_folder(self):
        """
        if this file is not in a specific folder return the Special "unfiled"
        Folder object
        """
        if not self.folder:
            from filer.models.virtualitems import UnfiledImages
            return UnfiledImages()
        else:
            return self.folder

    @property
    def logical_path(self):
        """
        Gets logical path of the folder in the tree structure.
        Used to generate breadcrumbs
        """
        folder_path = []
        if self.folder:
            folder_path.extend(self.folder.get_ancestors())
        folder_path.append(self.logical_folder)
        return folder_path

    @property
    def duplicates(self):
        return list(File.objects.find_duplicates(self))

    def is_readonly(self):
        if self.folder:
            return self.folder.is_readonly()
        return False

    def is_restricted_for_user(self, user):
        return (self.restricted and (
                    not user.has_perm('filer.can_restrict_operations') or
                    not can_restrict_on_site(user, self.folder.site)))

    def can_change_restricted(self, user):
        """
        Checks if restriction operation is available for this file.
        """
        if not user.has_perm('filer.can_restrict_operations'):
            return False
        if not self.folder:
            # cannot restrict unfiled files
            return False

        if not can_restrict_on_site(user, self.folder.site):
            return False

        if self.folder.restricted == self.restricted == True:
            # only parent can be set to True
            return False
        if self.folder.restricted == self.restricted == False:
            return True
        if self.folder.restricted == True and self.restricted == False:
            raise IntegrityError(
                'Re-save folder %s to fix restricted property' % (
                    self.folder.pretty_logical_path))
        return True

    def has_change_permission(self, user):
        if not self.folder:
            # clipboard and unfiled files
            return True

        if self.is_readonly():
            # nobody can change core folder
            # leaving these on True based on the fact that core folders are
            # displayed as readonly fields
             return True

        # only admins can change site folders with no site owner
        if not self.folder.site and has_admin_role(user):
            return True

        if self.folder.site:
            return (user.has_perm('filer.change_file') and
                    has_role_on_site(user, self.folder.site))

        return False

    def has_delete_permission(self, user):
        if not self.folder:
             # clipboard and unfiled files
             return True
        # nobody can delete core files
        if self.is_readonly():
             return False
        # only admins can delete site files with no site owner
        if not self.folder.site and has_admin_role(user):
             return True

        if self.folder.site:
            return (user.has_perm('filer.delete_file') and
                    has_role_on_site(user, self.folder.site))
        return False

    class Meta:
        app_label = 'filer'
        verbose_name = _('file')
        verbose_name_plural = _('files')
