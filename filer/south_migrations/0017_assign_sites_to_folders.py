# -*- coding: utf-8 -*-
import datetime, logging, re, difflib, collections
from south.db import db
from south.v2 import DataMigration
from django.db import models
from django.db.models import Q
from django.contrib.sites.models import Site
from django.contrib.auth.models import Group, User
from filer.utils.cms_roles import get_sites_for_user
from filer.utils.checktrees import TreeChecker
from cmsroles.models import Role


class Migration(DataMigration):

    depends_on = (
        ("cmsroles", "0003_rename_site_group"),
    )

    core_folders = ['media', '_bento_media']
    fallback_site = 'lunchbox.pbs.org'

    parent_sites_prefix = ['bcc2', 'shawfestival', 'standingbearsfootsteps',
        'program', 'westernperspective', 'explorerproducer', 'wkyu.',
        'kpts.',
        ]

    folders_to_site_prefix = {
        'FF-Site': 'firstfreedom',
        'SPI3_files': 'stationbento',
        'My Station Folderr': 'explorerproducer',
        'yif-static': 'yourinnerfish',
        'Great Plains': 'program',
        'Great Plains Extras': 'program',
        'address-preview-static': 'theaddresspreview',
        'Colores': 'NMPBS',
        'a': 'explorer-demo.',
        'BCC': 'bcc2',
        'Bento Academy': 'bento.',
        'Bento Explorer': 'bento.',
        'Hispanic-heritage-month': 'specials.',
        'PBS Moms Photo Gallery': 'specials.',
        'Patterns Library': 'designtest.',
        'Holiday Treatments': 'designtest.',
        'Sd-test-images': 'designtest.',
        'idptv_promo': 'exclusives.idaho',
        'KPTSHeaderArt': 'kpts.',
        'Mister Rogers Content': 'rogers.',
        'Mister Rogers Logos': 'rogers.',
        'PBS Arts': 'arts.',
        'PBS KIDS': 'pbskidsroku.',
        'Planet GO!': 'pbskids.',
        'RMPBS': 'www.rmpbs.',
        'RMPBS Buttons': 'www.rmpbs.',
        'RMPBS Events': 'www.rmpbs.',
        'WETP Icons': 'www.easttennesseepbs.',
        'wkno_MOW': 'marchonwashington.wkno.',
        'WSKG_User_Test': 'WSKG.'
    }

    folders_to_fallback_site = [
        '1abc', 'Branding', 'cat', 'editor folder', 'EmilyK-test',
        'filer folder demo', 'Folder-Delete-Test', 'Ghost Favicons',
        'harnessing', 'Header Logos', 'Jen', 'Markham', 'Markham Test',
        'MaxBento_files', 'MaxBento_images', 'My Station Folder',
        'Northwest Public Television-Test', 'rivers', 'RMPBS Test 1413',
        'SPI_Logo', 'SPI_Logos', 'SPI3_images', 'SPI3_logos', 'SPISD_files',
        'SPISD_images', 'SPISD_logos', 'writer folder', 'Test Folder 2',
        'Max_IDtest', 'content', 'DAC'
    ]

    station_pattern = 'www\.*(.+?)\.|(^.+?)\.'

    def init_logger(self):
        logger = logging.getLogger('assign_sites_to_folders')
        logger.setLevel(logging.INFO)
        log_file_name = 'assign_sites_to_folders_%s.log' % (
            datetime.datetime.now().strftime('%m_%d_%yT%H_%M_%S'), )
        fh = logging.FileHandler(log_file_name)
        fh.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s - %(message)s')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        logger.addHandler(fh)
        logger.addHandler(ch)
        self.log = logger

    def get_best_site_match(self, sites, match_with, valid_limit):
        site_match = {}
        for site in sites:
            station = re.search(self.station_pattern, site.domain).groups()
            station = max(station).lower()
            site_match[site.id] = difflib.SequenceMatcher(
                lambda x: x in " \t-'\"", match_with.lower(), station).ratio()

        if site_match:
            site_id = max(site_match.iterkeys(), key=lambda k: site_match[k])
            match_val = site_match[site_id]
            if match_val < valid_limit:
                return None
            return site_id
        return None

    def guess_site_by_owner_email(self, folder, candidates):
        if not folder.owner.email:
            return False

        station_email = re.search(
            '@(.+)\.', folder.owner.email).groups()[0]
        if station_email == 'pbs':
            if self.guess_site_by_folder_name(folder, candidates):
                return True
            self.log.info('\tfound owner with PBS email account')
            self.map_to_fallback_site(folder)
            return True

        best_site_match = self.get_best_site_match(
            candidates, station_email, 0.4)
        if best_site_match:
            self.log.info('\tfound owner email match')
            self.make_site_folder(
                folder, Site.objects.get(id=best_site_match))
            return True
        return False

    def guess_site_by_folder_name(self, folder, candidates):
        if len(folder.name) < 3:
            self.log.info('\tfolder name too short to be guessed')
            return False
        best_site_match = self.get_best_site_match(
            candidates, folder.name, 0.5)
        if best_site_match:
            self.log.info('\tfound folder name match')
            self.make_site_folder(
                folder, Site.objects.get(id=best_site_match))
            return True
        return False

    def guess_by_parent_site(self, folder, candidates):
        hardcoded_parents_q = Q(domain__iregex='www.*.org')
        for parent_station in self.parent_sites_prefix:
            hardcoded_parents_q |= Q(domain__startswith=parent_station)
        best_candidate = candidates.filter(hardcoded_parents_q)
        if best_candidate.count() == 1:
            self.log.info('\tFound parent site %s' % best_candidate[0])
            self.make_site_folder(folder, best_candidate[0])
            return True
        return False

    def map_defined_folders(self, folder):
        folder_name = folder.name.strip()
        if folder_name in self.folders_to_site_prefix:
            station_name = self.folders_to_site_prefix[folder_name]
            site = Site.objects.filter(domain__startswith=station_name)
            if site.count() == 1:
                self.log.info('\tFound defined folder that should be '
                              'mapped to %s' % site[0])
                self.make_site_folder(folder, site[0])
                return True
        elif folder_name in self.folders_to_fallback_site:
            self.map_to_fallback_site(folder)
            return True
        return False

    def map_to_fallback_site(self, folder, candidates=None):
        candidates = candidates or Site.objects.all()
        best_candidate = candidates.filter(domain=self.fallback_site)
        if best_candidate.exists():
            self.make_site_folder(folder, best_candidate[0])
            return True
        return False

    def guess_site_from_candidates(self, folder, candidates):
        self.log.info('\ttrying to find best candidate from %s' % (
            ', '.join(candidates.values_list('domain', flat=True))))

        if self.guess_site_by_folder_name(folder, candidates):
            self.share_site_folder(folder, candidates)
            return
        if self.guess_by_parent_site(folder, candidates):
            self.share_site_folder(folder, candidates)
            return
        if self.map_to_fallback_site(folder, candidates):
            self.share_site_folder(folder, candidates)
            return
        if self.guess_site_by_owner_email(folder, candidates):
            self.share_site_folder(folder, candidates)
            return
        self.log.error(
            "\tCouldn't guess site for folder %s from candidates: %s" % (
            folder.name, ', '.join(candidates.values_list('domain', flat=True))))

    def migrate_by_folderpermissions(self, folder, folder_perms):
        self.log.info("\ttrying to migrate by folder permission")
        perms_with_groups = folder_perms.filter(
            user__isnull=True, group__isnull=False, everybody=False)
        perms_with_users = folder_perms.filter(
            user__isnull=False, group__isnull=True, everybody=False)
        perms_for_everybody = folder_perms.filter(
            user__isnull=True, group__isnull=True, everybody=True)
        if perms_with_groups.exists():
            self.migrate_by_permission_with_groups(folder, perms_with_groups)
        elif perms_with_users.exists():
            self.migrate_by_permission_with_users(folder, perms_with_users)
        elif perms_for_everybody.exists():
            self.log.warn('\tNo way of migrating perms of type everybody')
            self.migrate_by_user(folder)
        else:
            self.log.warn('\tMESSED UP PERMISSIONS - has user and group')
            self.migrate_by_user(folder)

    def migrate_by_permission_with_groups(self, folder, folder_perms):
        self.log.info("\ttrying to migrate by perms with groups")
        groups = Group.objects.filter(
            id__in=folder_perms.values_list('group', flat=True).distinct())
        site_groups = groups.exclude(
            globalpagepermission__isnull=True)
        base_groups = groups.filter(
            globalpagepermission__isnull=True)
        if base_groups.exists():
            self.log.warn('\thas base groups assigned: %s' % ', '.join(
                base_groups.values_list('name', flat=True)))
        if site_groups.exists():
            self.log.info('\tfound site groups: %s' % ', '.join(
                site_groups.values_list('name', flat=True)))

            candidate_sites = site_groups.values_list(
                'globalpagepermission__sites__domain', flat=True).distinct()

            if len(candidate_sites) == 1:
                self.make_site_folder(
                    folder, Site.objects.get(domain=candidate_sites[0]))
            else:
                self.guess_site_from_candidates(
                    folder, Site.objects.filter(domain__in=candidate_sites))
        else:
            self.log.warn('\tMESSED UP GROUPS (no site groups found)')
            self.migrate_by_user(folder)

    def _user_with_sites_str(self, user):
        available_sites = Site.objects.filter(
            id__in=get_sites_for_user(user)).values_list(
            'domain', flat=True) or ['No roles on any sites']
        status = 'superuser' if user.is_superuser else 'regular'
        return '%s (%s: %s)' % (user.email or user.username, status,
                                ', '.join(available_sites))

    def migrate_by_permission_with_users(self, folder, folder_perms):
        self.log.info("\ttrying to migrate by perms with users")
        users = User.objects.filter(
            id__in=folder_perms.values_list('user', flat=True).distinct())
        if users.count() == 1:
            self.migrate_by_user(folder, users[0])
        else:
            self.log.info('\tusing users: %s' % '; '.join(
                [self._user_with_sites_str(user)
                 for user in users]))

            list_with_sites = []

            for user in users:
                list_with_sites.append(get_sites_for_user(user))

            all_users_sites = set.union(*list_with_sites)
            common_users_sites = set.intersection(*list_with_sites)

            if len(common_users_sites) == 0:
                self.log.info('\tno common sites found')
                self.guess_site_from_candidates(
                    folder, Site.objects.filter(id__in=all_users_sites))
            elif len(common_users_sites) == 1:
                site_found = Site.objects.get(id__in=common_users_sites)
                self.log.info('\tfound one common site %s' % (
                    site_found.domain))
                self.make_site_folder(folder, site_found)
            else:
                common_users_sites = Site.objects.filter(
                    id__in=common_users_sites)
                self.log.info('\tfound more common sites %s' % (
                    ', '.join(common_users_sites.values_list(
                                'domain', flat=True))))
                self.guess_site_from_candidates(folder, common_users_sites)

    def migrate_by_user(self, folder, user=None):
        if not user:
            user = folder.owner
            self.log.info("\tusing folder owner")

        self.log.info("\ttrying to migrate by user %s" % (
            self._user_with_sites_str(user), ))

        user_sites = get_sites_for_user(user)
        if len(user_sites) == 1:
            self.make_site_folder(folder, Site.objects.get(id__in=user_sites))
        elif len(user_sites) == 0:
            self.log.error("user doesn't have any roles on any sites")
            if self.guess_site_by_owner_email(folder, Site.objects.all()):
                return
            self.map_to_fallback_site(folder)
        else:
            self.guess_site_from_candidates(
                folder, Site.objects.filter(id__in=user_sites))

    def make_core_folder(self, folder):
        self.log.info("\tSUCCESS: core folder")
        folder = self.folder_cls.objects.get(id=folder.id)
        folder.get_descendants(include_self=True).update(
            folder_type=1, site=None)
        self.folders_migrated.add(folder.id)

    def make_site_folder(self, folder, site):
        self.log.info('\tSUCCESS: folder binded to %s' % site.domain)
        folder = self.folder_cls.objects.get(id=folder.id)
        folder.get_descendants(include_self=True).update(site=site)
        self.folders_migrated.add(folder.id)

    def share_site_folder(self, folder, sites):
        folder = self.folder_cls.objects.get(id=folder.id)
        if not folder.folder_type == 1:
            folder.shared.add(*sites)
        self.log.info('\tSUCCESS: folder shared with %s' % ', '.join(
            [s.domain for s in sites]))

    def fix_tree(self):
        self.log.info("Fixing folder trees.")
        TreeChecker(self.folder_cls.objects).rebuild()
        self.log.info("Folder trees fixed.")

    def forwards(self, orm):
        self.folder_cls = orm.Folder
        if not self.folder_cls.objects.exists():
            return

        self.init_logger()
        self.fix_tree()

        self.folders_migrated = set()
        FolderPermission = orm.FolderPermission
        root_folders = self.folder_cls.objects.filter(parent__isnull=True)
        for folder in root_folders:
            self.log.info("Folder: %s" % folder.name)
            if folder.name in self.core_folders:
                self.make_core_folder(folder)
                continue
            if self.map_defined_folders(folder):
                continue
            folder_perms = FolderPermission.objects.filter(folder=folder)
            if folder_perms.exists():
                self.migrate_by_folderpermissions(folder, folder_perms)
                continue
            self.migrate_by_user(folder)

        self.log.info(('\n{:=^50}' * 3).format('=', "Migration Summary", '='))

        self.log.info("\nFollowing folders were migrated with success\n")
        for folder_id in self.folders_migrated:
            folder = self.folder_cls.objects.get(id=folder_id)
            self.log.info("%s | %s | %s" % (
                folder.name,
                'Core Folder' if folder.folder_type == 1 else folder.site.domain,
                ', '.join(folder.shared.values_list('domain', flat=True))))

        orphans = root_folders.exclude(id__in=self.folders_migrated)
        if orphans.count() == 0:
            return
        self.log.info('\nFollowing folders will remain with no site assigned\n')
        for folder in orphans:
            self.log.info(folder.name)

    def backwards(self, orm):
        "No going back"

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.archive': {
            'Meta': {'object_name': 'Archive', '_ormbases': ['filer.File']},
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'})
        },
        'filer.clipboard': {
            'Meta': {'object_name': 'Clipboard'},
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'in_clipboards'", 'symmetrical': 'False', 'through': "orm['filer.ClipboardItem']", 'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'filer_clipboards'", 'to': "orm['auth.User']"})
        },
        'filer.clipboarditem': {
            'Meta': {'object_name': 'ClipboardItem'},
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'filer.file': {
            'Meta': {'object_name': 'File'},
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.FileField', [], {'db_index': 'True', 'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'polymorphic_ctype': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'polymorphic_filer.file_set'", 'null': 'True', 'to': "orm['contenttypes.ContentType']"}),
            'restricted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'sha1': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '40', 'blank': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('parent', 'name'),)", 'object_name': 'Folder'},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'folder_type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'restricted': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'shared': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'shared'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['sites.Site']"}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']", 'null': 'True', 'blank': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folderpermission': {
            'Meta': {'object_name': 'FolderPermission'},
            'can_add_children': ('django.db.models.fields.SmallIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'can_edit': ('django.db.models.fields.SmallIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'can_read': ('django.db.models.fields.SmallIntegerField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_folder_permissions'", 'null': 'True', 'to': "orm['auth.Group']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'filer_folder_permissions'", 'null': 'True', 'to': "orm['auth.User']"})
        },
        'filer.image': {
            'Meta': {'object_name': 'Image', '_ormbases': ['filer.File']},
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_credit': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['filer']
    symmetrical = True
