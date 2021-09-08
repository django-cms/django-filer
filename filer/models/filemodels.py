#-*- coding: utf-8 -*-
import polymorphic
import hashlib
import os
import filer
import logging
import operator

from django.contrib.auth import models as auth_models
from django.urls import reverse
from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.db import (models, IntegrityError, transaction)
from django.utils.translation import ugettext_lazy as _
from filer.fields.multistorage_file import MultiStorageFileField
from filer.models import mixins
from filer.utils.cms_roles import *
from filer.utils.files import matching_file_subtypes
from filer import settings as filer_settings
from django.db.models import Count
from django.utils import timezone

from polymorphic.models import PolymorphicModel
from polymorphic.managers import PolymorphicManager
from polymorphic.query import PolymorphicQuerySet
import hashlib
import os
import filer
import logging

logger = logging.getLogger(__name__)


def silence_error_if_missing_file(exception):
    """
    Ugly way of checking in an exception describes a 'missing file'.
    """
    missing_files_errs = ('no such file', 'does not exist', )

    def find_msg_in_error(msg):
        return msg in str(exception).lower()

    if not any(map(find_msg_in_error, missing_files_errs)):
        raise exception


class FileQuerySet(PolymorphicQuerySet):

    def readonly(self, user):
        Folder = filer.models.foldermodels.Folder
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


class FileManager(PolymorphicManager):
    queryset_class = FileQuerySet

    def find_all_duplicates(self):
        return {file_data['sha1']: file_data['count']
                for file_data in self.get_queryset().values('sha1').annotate(
                    count=Count('id')).filter(count__gt=1)}


class AliveFileManager(FileManager):
    # this is required in order to make sure that other models that are
    #   related to filer files will get an DoesNotExist exception if the file
    #   is in trash
    use_for_related_fields = True

    def get_queryset(self):
        return super(AliveFileManager, self).get_queryset().filter(
            deleted_at__isnull=True)


class TrashFileManager(FileManager):

    def get_queryset(self):
        return super(TrashFileManager, self).get_queryset().filter(
            deleted_at__isnull=False)


@mixins.trashable
class File(PolymorphicModel,
           mixins.IconsMixin):

    file_type = 'File'
    _icon = "file"
    folder = models.ForeignKey('filer.Folder', verbose_name=_('folder'), related_name='all_files',
        null=True, blank=True, on_delete=models.deletion.CASCADE)
    file = MultiStorageFileField(_('file'), null=True, blank=True, db_index=True, max_length=255)
    _file_size = models.IntegerField(_('file size'), null=True, blank=True)

    sha1 = models.CharField(_('sha1'), max_length=40, blank=True, default='')

    has_all_mandatory_data = models.BooleanField(_('has all mandatory data'), default=False, editable=False)

    original_filename = models.CharField(_('original filename'), max_length=255, blank=True, null=True)
    name = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_('file name'),
        help_text=_('Change the FILE name for an image in the cloud storage'
                    ' system; be sure to include the extension '
                    '(.jpg or .png, for example) to ensure asset remains '
                    'valid.'))
    title = models.CharField(
        max_length=255, null=True, blank=True, verbose_name=_('name'),
        help_text=_('Used in the Photo Gallery plugin as a title or name for'
                    ' an image; not displayed via the image plugin.'))
    description = models.TextField(
        null=True, blank=True, verbose_name=_('description'),
        help_text=_('Used in the Photo Gallery plugin as a description;'
                    ' not displayed via the image plugin.'))

    owner = models.ForeignKey(auth_models.User,
        related_name='owned_%(class)ss', on_delete=models.SET_NULL,
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

    objects = AliveFileManager()
    trash = TrashFileManager()
    all_objects = FileManager()

    @classmethod
    def matches_file_type(cls, iname, ifile, request):
        return True  # I match all files...

    def __init__(self, *args, **kwargs):
        super(File, self).__init__(*args, **kwargs)
        self._old_is_public = self.is_public
        self._old_sha1 = self.sha1
        self._force_commit = False
        # see method _is_path_changed
        self._old_name = self.name
        self._current_file_location = self.file.name
        self._old_folder_id = self.folder_id

    def clean(self):
        if self.name:
            self.name = self.name.strip()
            if "/" in self.name:
                raise ValidationError(
                    "Slashes are not allowed in file names.")
            extension = os.path.splitext(self.name)[1]
            if not extension:
                raise ValidationError(
                    "File name without extension is not allowed.")

            old_file_type = self.get_real_instance_class()
            new_file_type = matching_file_subtypes(self.name, None, None)[0]

            if not old_file_type is new_file_type:
                supported_extensions = getattr(
                    old_file_type, '_filename_extensions', [])
                if supported_extensions:
                    err_msg = "File name (%s) for this %s should preserve " \
                              "one of the supported extensions %s" % (
                                self.name, old_file_type.file_type.lower(),
                                ', '.join(supported_extensions))
                else:
                    err_msg = "Extension %s is not allowed for this file " \
                              "type." % (extension, )
                raise ValidationError(err_msg)

        if self.folder:
            entries = self.folder.entries_with_names([self.actual_name])
            if entries and any(entry.pk != self.pk for entry in entries):
                raise ValidationError(
                    _('Current folder already contains a file named %s') % \
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
        src_file.close()
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

        src_file_name = self._current_file_location
        storage = self.file.storages['public' if self.is_public else 'private']

        if hasattr(storage, 'copy'):
            storage.copy(src_file_name, destination)
        else:
            # This is needed because most of the remote File Storage backend do not
            # open the file.
            src_file = storage.open(src_file_name)
            src_file.open()
            destination = storage.save(destination,
                                       ContentFile(src_file.read()))
            src_file.close()
        self._current_file_location = destination
        self.old_name = self.name
        self._old_folder_id = getattr(self.folder, 'id', None)
        return destination

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
        except (IOError, TypeError, ValueError) as e:
            pass
        if filer_settings.FOLDER_AFFECTS_URL and self._is_path_changed():
            self._force_commit = True
            self.update_location_on_storage(*args, **kwargs)
        else:
            super(File, self).save(*args, **kwargs)

    save.alters_data = True

    def _is_path_changed(self):
        """
        Used to detect if file location on storage should be updated or not.
        Since this is used only to check if location should be updated,
            the values will be reset after the file is copied in the
            destination location on storage.
        """
        # check if file name changed
        if self._old_name in ('', None):
            name_changed = self.name not in ('', None)
        else:
            name_changed = self._old_name != self.name

        folder_changed = self._old_folder_id != getattr(self.folder, 'id', None)

        return name_changed or folder_changed

    def _delete_thumbnails(self):
        source = self.file.get_source_cache()
        if source:
            self.file.delete_thumbnails()
            source.delete()

    def update_location_on_storage(self, *args, **kwargs):
        old_location = self._current_file_location
        # thumbnails might get physically deleted evenif the transaction fails
        # though luck... they get re-created anyway...
        self._delete_thumbnails()
        # check if file content has changed
        if self._old_sha1 != self.sha1:
            # actual file content needs to be replaced on storage prior to
            #   filer file instance save
            self.file.storage.save(self._current_file_location, self.file)
            self._old_sha1 = self.sha1
        new_location = self.file.field.upload_to(self, self.actual_name)
        storage = self.file.storage

        def copy_and_save():
            saved_as = self._copy_file(new_location)
            assert saved_as == new_location, '%s %s' % (saved_as, new_location)
            self.file = saved_as
            super(File, self).save(*args, **kwargs)

        if self._force_commit:
            try:
                with transaction.atomic(savepoint=False):
                    # The manual transaction management here breaks the transaction management
                    # from django.contrib.admin.options.ModelAdmin.change_view
                    # This isn't a big problem because the only CRUD operation done afterwards
                    # is an insertion in django_admin_log. If this method rollbacks the transaction
                    # then we will have an entry in the admin log describing an action
                    # that didn't actually finish succesfull.
                    # This 'hack' can be removed once django adds support for on_commit and
                    # on_rollback hooks (see: https://code.djangoproject.com/ticket/14051)
                    copy_and_save()
            except:
                # delete the file from new_location if the db update failed
                if old_location != new_location:
                    storage.delete(new_location)
                raise
            else:
                # only delete the file on the old_location if all went OK
                if old_location != new_location:
                    storage.delete(old_location)
        else:
            copy_and_save()
        return new_location

    def soft_delete(self, *args, **kwargs):
        """
        This method works as a default delete action of a filer file.
        It will not actually delete the item from the database, instead it
            will make it inaccessible for the default manager.
        It just `fakes` a deletion by doing the following:
            1. sets a deletion time that will be used to distinguish
                `alive` and `trashed` filer files.
            2. makes a copy of the actual file on storage and saves it to
                a trash location on storage. Also tries to ignore if the
                actual file is missing from storage.
            3. updates only the filer file path in the database (no model
                save is done since it tries to bypass the logic defined
                in the save method)
            4. deletes the file(and all it's thumbnails) from the
                original location if no other filer files are referencing
                it.
        All the metadata of this filer file will remain intact.
        """
        deletion_time = kwargs.pop('deletion_time', timezone.now())
        # move file to a `trash` location
        to_trash = filer.utils.generate_filename.get_trash_path(self)
        old_location, new_location = self.file.name, None
        try:
            new_location = self._copy_file(to_trash)
        except Exception as e:
            silence_error_if_missing_file(e)
            if filer_settings.FILER_ENABLE_LOGGING:
                logger.error('Error while trying to copy file: %s to %s.' % (
                    old_location, to_trash), e)
        else:
            # if there are no more references to the file on storage delete it
            #   and all its thumbnails
            if not File.objects.exclude(pk=self.pk).filter(
                file=old_location, is_public=self.is_public).exists():
                self.file.delete(False)
        finally:
            # even if `copy_file` fails, user is trying to delete this file so
            #   in worse case scenario this file is not restorable
            new_location = new_location or to_trash
            File.objects.filter(pk=self.pk).update(
                deleted_at=deletion_time, file=new_location)

            self.deleted_at = deletion_time
            self.file = new_location

    def hard_delete(self, *args, **kwargs):
        """
        This method deletes the filer file from the database and from storage.
        """
        # delete the model before deleting the file from storage
        super(File, self).delete(*args, **kwargs)
        # delete the actual file from storage and all its thumbnails
        #   if there are no other filer files referencing it.
        if not File.objects.filter(file=self.file.name,
                                   is_public=self.is_public).exists():
            self.file.delete(False)

    def delete(self, *args, **kwargs):
        super(File, self).delete_restorable(*args, **kwargs)
    delete.alters_data = True

    def _set_valid_name_for_restore(self):
        """
        Generates the first available name so this file
            can be restored in the folder.
        """
        basename, extension = os.path.splitext(self.clean_actual_name)
        if self.folder:
            files = self.folder.files
        elif self.owner:
            files = filer.models.tools.get_user_clipboard(self.owner).files.all()
        else:
            from filer.models.virtualitems import UnfiledImages
            files = UnfiledImages().files
        existing_file_names = [f.clean_actual_name for f in files]
        i = 1
        while self.clean_actual_name in existing_file_names:
            filename = "%s_%s%s" % (basename, i, extension)
            # set actual name
            if self.name in ('', None):
                self.original_filename = filename
            else:
                self.name = filename
            i += 1

    def restore(self):
        """
            Restores the file to its folder location.
            If there's already an existing file with the same name, it will
                generate a new filename.
        """
        if self.folder_id:
            Folder = filer.models.foldermodels.Folder
            try:
                self.folder
            except Folder.DoesNotExist:
                self.folder = Folder.trash.get(id=self.folder_id)

            self.folder.restore_path()
            # at this point this file's folder should be `alive`
            self.folder = filer.models.Folder.objects.get(id=self.folder_id)

        old_location, new_location = self.file.name, None
        self._set_valid_name_for_restore()
        destination = self.file.field.upload_to(self, self.upload_to_name)
        try:
            new_location = self._copy_file(destination)
        except Exception as e:
            silence_error_if_missing_file(e)
            if filer_settings.FILER_ENABLE_LOGGING:
                logger.error('Error while trying to copy file: %s to %s.' % (
                    old_location, destination), e)
        else:
            self.file.delete(False)
        finally:
            new_location = new_location or destination
            File.trash.filter(pk=self.pk).update(
                deleted_at=None, file=new_location,
                name=self.name, original_filename=self.original_filename)
            self.deleted_at = None
            self.file.name = new_location
            # restore to user clipboard
            if self.owner_id and not self.folder_id:
                clipboard = filer.models.tools.get_user_clipboard(self.owner)
                clipboard.append_file(File.objects.get(id=self.id))

    @property
    def label(self):
        if self.name in ['', None]:
            text = self.original_filename or 'unnamed file'
        else:
            text = self.name
        text = "%s" % (text,)
        return text

    def _cmp(self, a, b):
        return (a > b) - (a < b) 

    def __lt__(self, other):
        return self._cmp(self.label.lower(), other.label.lower()) < 0

    @property
    def actual_name(self):
        if not self.sha1:
            try:
                self.generate_sha1()
            except (IOError, TypeError, ValueError):
                return self.clean_actual_name
        try:
            folder = self.folder.get_ancestors().first()
            root_folder = getattr(folder, 'name', None)
        except:
            root_folder = None
        if root_folder in filer_settings.FILER_NOHASH_ROOTFOLDERS:
            name_fmt = '{actual_name}'
        else:
            name_fmt = '{hashcode}_{actual_name}'
        name = name_fmt.format(hashcode=self.sha1[:10],
                               actual_name=self.clean_actual_name)
        return name

    @property
    def upload_to_name(self):
        """
        For normal files this is the actual name with the hash but clipboard
        file upload locations are the clean names.
        """
        if self.folder:
            return self.actual_name
        else:
            return self.clean_actual_name

    @property
    def clean_actual_name(self):
        """The name displayed to the user.
        Uses self.name if set, otherwise it falls back on self.original_filename.

        This property is used for enforcing unique filenames within the same folder.
        """
        if self.name in ('', None):
            name = "%s" % (self.original_filename,)
        else:
            name = "%s" % (self.name,)
        return name

    @property
    def pretty_logical_path(self):
        its_dir = self.logical_folder
        if its_dir.is_root:
            directory_path = ''
        else:
            directory_path = its_dir.pretty_logical_path
        full_path = '{}{}{}'.format(directory_path, os.sep, self.actual_name)
        return full_path

    def __unicode__(self):
        try:
            name = self.pretty_logical_path
        except:
            name = self.actual_name
        return name

    def get_admin_url_path(self):
        return reverse(
            'admin:%s_%s_change' % (self._meta.app_label,
                                    self._meta.model_name,),
            args=(self.pk,)
        )

    def get_admin_delete_url(self):
        return reverse(
            'admin:{0}_{1}_delete'.format(self._meta.app_label, self._meta.model_name,),
            args=(self.pk,))

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

    def is_core(self):
        if self.folder:
            return self.folder.is_core()
        return False

    def is_readonly_for_user(self, user):
        if self.folder:
            return self.folder.is_readonly_for_user(user)
        return False

    def is_restricted_for_user(self, user):
        perm = 'filer.can_restrict_operations'
        return (self.restricted and (
            not (user.has_perm(perm, self) or user.has_perm(perm)) or
            not can_restrict_on_site(user, self.folder.site)))

    def can_change_restricted(self, user):
        """
        Checks if restriction operation is available for this file.
        """
        perm = 'filer.can_restrict_operations'
        if not user.has_perm(perm, self) and not user.has_perm(perm):
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

        if self.is_readonly_for_user(user):
            # nobody can change core folder
            # leaving these on True based on the fact that core folders are
            # displayed as readonly fields
            return True

        # only admins can change site folders with no site owner
        if not self.folder.site and has_admin_role(user):
            return True

        if self.folder.site:
            can_change_file = (user.has_perm('filer.change_file', self) or
                               user.has_perm('filer.change_file'))
            return can_change_file and has_role_on_site(user, self.folder.site)

        return False

    def has_delete_permission(self, user):
        if not self.folder:
             # clipboard and unfiled files
            return True
        # nobody can delete core files
        if self.is_readonly_for_user(user):
            return False
        # only admins can delete site files with no site owner
        if not self.folder.site and has_admin_role(user):
            return True

        if self.folder.site:
            can_delete_file = (user.has_perm('filer.delete_file', self) or
                               user.has_perm('filer.delete_file'))
            return can_delete_file and has_role_on_site(user, self.folder.site)
        return False

    def __str__(self):
        return self.__unicode__()
    class Meta:
        app_label = 'filer'
        verbose_name = _('file')
        verbose_name_plural = _('files')
