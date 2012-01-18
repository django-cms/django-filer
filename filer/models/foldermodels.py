import mptt
from django.utils.translation import ugettext_lazy as _
from django.db import models
from django.db.models import Q
from django.contrib.auth import models as auth_models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.core import urlresolvers
from filer.models import mixins

'''
Managers
'''
class FolderManager(models.Manager):    
    def with_bad_metadata(self):
        return self.get_query_set().filter(has_all_mandatory_data=False)

class FolderPermissionManager(models.Manager):
    def get_read_id_list(self, user):
        """
        Give a list of a Folders where the user has read rights or the string
        "All" if the user has all rights.
        """
        return self.__get_id_list(user, "can_read")
    def get_edit_id_list(self, user):
        return self.__get_id_list(user, "can_edit")
    def get_add_children_id_list(self, user):
        return self.__get_id_list(user, "can_add_children")
    def __get_id_list(self, user, attr):
        if user.is_superuser:
            return 'All'
        allow_list = []
        deny_list = []
        group_ids = user.groups.all().values_list('id', flat=True)
        q = Q(user=user)|Q(group__in=group_ids)|Q(everybody=True)
        perms = self.filter(q).order_by('folder__tree_id', 'folder__level', 
                                        'folder__lft')
        for perm in perms:
            if perm.folder:
                folder_id = perm.folder.id
            else:
                folder_id = None
            if perm.type == FolderPermission.ALL:
                if getattr(perm, attr):
                    allow_list = list(Folder.objects.all().values_list('id', flat=True))
                else:
                    return []
            if getattr(perm, attr):
                if folder_id not in allow_list:
                    allow_list.append(folder_id)
                if folder_id in deny_list:
                    deny_list.remove(folder_id)
            else:
                if folder_id not in deny_list:
                    deny_list.append(folder_id)
                if folder_id in allow_list:
                    allow_list.remove(folder_id)
            if perm.type == FolderPermission.CHILDREN:
                for id in perm.folder.get_descendants().values_list('id', flat=True):
                    if getattr(perm, attr):
                        if id not in allow_list:
                            allow_list.append(id)
                        if id in deny_list:
                            deny_list.remove(id)
                    else:
                        if id not in deny_list:
                            deny_list.append(id)
                        if id in allow_list:
                            allow_list.remove(id)
        return allow_list
    
'''
Models
'''
class Folder(models.Model, mixins.IconsMixin):
    """
    Represents a Folder that things (files) can be put into. Folders are *NOT*
    mirrored in the Filesystem and can have any unicode chars as their name.
    Other models may attach to a folder with a ForeignKey. If the related name
    ends with "_files" they will automatically be listed in the 
    folder.files list along with all the other models that link to the folder
    in this way. Make sure the linked models obey the AbstractFile interface
    (Duck Type).
    """
    file_type = 'Folder'
    is_root = False
    can_have_subfolders = True
    _icon = 'plainfolder'
    
    parent = models.ForeignKey('self', null=True, blank=True, related_name='children')
    name = models.CharField(max_length=255, verbose_name=_('name'))
    
    owner = models.ForeignKey(auth_models.User, related_name='filer_owned_folders', null=True, blank=True, verbose_name=_('owner'))
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    
    objects = FolderManager()
    
    @property
    def file_count(self):
        if not hasattr(self, '_file_count_cache'):
            self._file_count_cache = self.files.count()
        return self._file_count_cache
    @property
    def children_count(self):
        if not hasattr(self, '_children_count_cache'):
            self._children_count_cache = self.children.count()
        return self._children_count_cache
    @property
    def item_count(self):
        return self.file_count + self.children_count
    @property
    def files(self):
        return self.all_files.all()
    @property
    def logical_path(self):
        """
        Gets logical path of the folder in the tree structure.
        Used to generate breadcrumbs
        """
        folder_path = []
        if self.parent:
            folder_path.extend(self.parent.get_ancestors())
            folder_path.append(self.parent)
        return folder_path
    
    def has_edit_permission(self, request):
        return self.has_generic_permission(request, 'edit')
    def has_read_permission(self, request):
        return self.has_generic_permission(request, 'read')
    def has_add_children_permission(self, request):
        return self.has_generic_permission(request, 'add_children')
    def has_generic_permission(self, request, type):
        """
        Return true if the current user has permission on this
        folder. Return the string 'ALL' if the user has all rights.
        """
        user = request.user
        if not user.is_authenticated() or not user.is_staff:
            return False
        elif user.is_superuser:
            return True
        elif user == self.owner:
            return True
        else:
            att_name = "permission_%s_cache" % type
            if not hasattr(self, "permission_user_cache") or \
               not hasattr(self, att_name) or \
               request.user.pk != self.permission_user_cache.pk:
                func = getattr(FolderPermission.objects, "get_%s_id_list" % type)
                permission = func(user)
                self.permission_user_cache = request.user
                if permission == "All" or self.id in permission:
                    setattr(self, att_name, True)
                    self.permission_edit_cache = True
                else:
                    setattr(self, att_name, False)
            return getattr(self, att_name)
    def get_admin_url_path(self):
        return urlresolvers.reverse('admin:filer_folder_change', args=(self.id,))
    def get_admin_directory_listing_url_path(self):
        return urlresolvers.reverse('admin:filer-directory_listing', args=(self.id,))
        
    def __unicode__(self):
        return u"%s" % (self.name,)
    class Meta:
        verbose_name = _('Folder')
        verbose_name_plural = _('Folders')
        unique_together = (('parent','name'),)
        ordering = ('name',)
        permissions = (("can_use_directory_listing", "Can use directory listing"),)
        app_label = 'filer'

# MPTT registration
try:
    mptt.register(Folder)
except mptt.AlreadyRegistered:
    pass
            
class FolderPermission(models.Model):
    ALL = 0
    THIS = 1
    CHILDREN = 2
    
    TYPES = (
        (ALL, _('all items') ),
        (THIS, _('this item only') ),
        (CHILDREN, _('this item and all children') ),
    )
    folder = models.ForeignKey(Folder, null=True, blank=True, verbose_name=_("folder"))
    
    type = models.SmallIntegerField(_('type'), choices=TYPES, default=0)
    user = models.ForeignKey(auth_models.User, related_name="filer_folder_permissions", verbose_name=_("user"), blank=True, null=True)
    group = models.ForeignKey(auth_models.Group, related_name="filer_folder_permissions", verbose_name=_("group"), blank=True, null=True)
    everybody = models.BooleanField(_("everybody"), default=False)
    
    can_edit = models.BooleanField(_("can edit"), default=True)
    can_read = models.BooleanField(_("can read"), default=True)
    can_add_children = models.BooleanField(_("can add children"), default=True)
    
    objects = FolderPermissionManager()
    
    def __unicode__(self):
        if self.folder:
            name = u'%s' % self.folder
        else:
            name = u'All Folders'
        
        ug = []
        if self.everybody:
            user = 'Everybody'
        else:
            if self.group:
                ug.append(u"Group: %s" % self.group)
            if self.user:
                ug.append(u"User: %s" % self.user)
        usergroup = " ".join(ug)
        perms = []
        for s in ['can_edit', 'can_read', 'can_add_children']:
            if getattr(self, s):
                perms.append(s)
        perms = ', '.join(perms)
        return u"Folder: '%s'->%s [%s] [%s]" % (name, unicode(self.TYPES[self.type][1]), perms, usergroup)
    class Meta:
        verbose_name = _('Folder Permission')
        verbose_name_plural = _('Folder Permissions')
        app_label = 'filer'
