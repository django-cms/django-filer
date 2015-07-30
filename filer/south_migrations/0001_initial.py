
from south.db import db
from django.db import models
from filer.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'Image'
        db.create_table('filer_image', (
            ('file_ptr', orm['filer.Image:file_ptr']),
            ('_height', orm['filer.Image:_height']),
            ('_width', orm['filer.Image:_width']),
            ('date_taken', orm['filer.Image:date_taken']),
            ('default_alt_text', orm['filer.Image:default_alt_text']),
            ('default_caption', orm['filer.Image:default_caption']),
            ('author', orm['filer.Image:author']),
            ('must_always_publish_author_credit', orm['filer.Image:must_always_publish_author_credit']),
            ('must_always_publish_copyright', orm['filer.Image:must_always_publish_copyright']),
            ('subject_location', orm['filer.Image:subject_location']),
        ))
        db.send_create_signal('filer', ['Image'])
        
        # Adding model 'ClipboardItem'
        db.create_table('filer_clipboarditem', (
            ('id', orm['filer.ClipboardItem:id']),
            ('file', orm['filer.ClipboardItem:file']),
            ('clipboard', orm['filer.ClipboardItem:clipboard']),
        ))
        db.send_create_signal('filer', ['ClipboardItem'])
        
        # Adding model 'File'
        db.create_table('filer_file', (
            ('id', orm['filer.File:id']),
            ('folder', orm['filer.File:folder']),
            ('file_field', orm['filer.File:file_field']),
            ('_file_type_plugin_name', orm['filer.File:_file_type_plugin_name']),
            ('_file_size', orm['filer.File:_file_size']),
            ('has_all_mandatory_data', orm['filer.File:has_all_mandatory_data']),
            ('original_filename', orm['filer.File:original_filename']),
            ('name', orm['filer.File:name']),
            ('owner', orm['filer.File:owner']),
            ('uploaded_at', orm['filer.File:uploaded_at']),
            ('modified_at', orm['filer.File:modified_at']),
        ))
        db.send_create_signal('filer', ['File'])
        
        # Adding model 'Folder'
        db.create_table('filer_folder', (
            ('id', orm['filer.Folder:id']),
            ('parent', orm['filer.Folder:parent']),
            ('name', orm['filer.Folder:name']),
            ('owner', orm['filer.Folder:owner']),
            ('uploaded_at', orm['filer.Folder:uploaded_at']),
            ('created_at', orm['filer.Folder:created_at']),
            ('modified_at', orm['filer.Folder:modified_at']),
            ('lft', orm['filer.Folder:lft']),
            ('rght', orm['filer.Folder:rght']),
            ('tree_id', orm['filer.Folder:tree_id']),
            ('level', orm['filer.Folder:level']),
        ))
        db.send_create_signal('filer', ['Folder'])
        
        # Adding model 'Clipboard'
        db.create_table('filer_clipboard', (
            ('id', orm['filer.Clipboard:id']),
            ('user', orm['filer.Clipboard:user']),
        ))
        db.send_create_signal('filer', ['Clipboard'])
        
        # Adding model 'FolderPermission'
        db.create_table('filer_folderpermission', (
            ('id', orm['filer.FolderPermission:id']),
            ('folder', orm['filer.FolderPermission:folder']),
            ('type', orm['filer.FolderPermission:type']),
            ('user', orm['filer.FolderPermission:user']),
            ('group', orm['filer.FolderPermission:group']),
            ('everybody', orm['filer.FolderPermission:everybody']),
            ('can_edit', orm['filer.FolderPermission:can_edit']),
            ('can_read', orm['filer.FolderPermission:can_read']),
            ('can_add_children', orm['filer.FolderPermission:can_add_children']),
        ))
        db.send_create_signal('filer', ['FolderPermission'])
        
        # Creating unique_together for [parent, name] on Folder.
        db.create_unique('filer_folder', ['parent_id', 'name'])
        
    
    
    def backwards(self, orm):
        
        # Deleting unique_together for [parent, name] on Folder.
        db.delete_unique('filer_folder', ['parent_id', 'name'])
        
        # Deleting model 'Image'
        db.delete_table('filer_image')
        
        # Deleting model 'ClipboardItem'
        db.delete_table('filer_clipboarditem')
        
        # Deleting model 'File'
        db.delete_table('filer_file')
        
        # Deleting model 'Folder'
        db.delete_table('filer_folder')
        
        # Deleting model 'Clipboard'
        db.delete_table('filer_clipboard')
        
        # Deleting model 'FolderPermission'
        db.delete_table('filer_folderpermission')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'filer.clipboard': {
            'files': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'clipboards'", 'to': "orm['auth.User']"})
        },
        'filer.clipboarditem': {
            'clipboard': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Clipboard']"}),
            'file': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.File']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'filer.file': {
            '_file_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_file_type_plugin_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'file_field': ('django.db.models.fields.files.FileField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'all_files'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'has_all_mandatory_data': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'original_filename': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_files'", 'null': 'True', 'to': "orm['auth.User']"}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folder': {
            'Meta': {'unique_together': "(('parent', 'name'),)"},
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'modified_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'owned_folders'", 'null': 'True', 'to': "orm['auth.User']"}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'children'", 'null': 'True', 'to': "orm['filer.Folder']"}),
            'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'uploaded_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'})
        },
        'filer.folderpermission': {
            'can_add_children': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_edit': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'can_read': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'everybody': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'folder': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['filer.Folder']", 'null': 'True', 'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.Group']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'filer.image': {
            '_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            '_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'author': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'date_taken': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'default_alt_text': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'default_caption': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True', 'blank': 'True'}),
            'file_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['filer.File']", 'unique': 'True', 'primary_key': 'True'}),
            'must_always_publish_author_credit': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'must_always_publish_copyright': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'subject_location': ('django.db.models.fields.CharField', [], {'default': 'None', 'max_length': '64', 'null': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['filer']
