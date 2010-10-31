# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from esp.dbmail.models import EmailList
from esp import settings

class Migration(SchemaMigration):

    def forwards(self, orm):
        #   Create default e-mail lists, only if they don't exist.
        list, created = EmailList.objects.get_or_create(regex='^(.*)$', handler='PlainList')
        if created:
            list.description = 'Manual Email List Redirects'
            list.seq = 0
            list.save()
        
        list, created = EmailList.objects.get_or_create(regex='^\w(\d+)s(\d+)-(class|teachers|students)$', handler='SectionList')
        if created:
            list.description = 'Individual sections of a class'
            list.seq = 4
            list.save()
        
        list, created = EmailList.objects.get_or_create(regex='^\w(\d+)-(class|teachers|students)$', handler='ClassList')
        if created:
            list.description='Email Class Rosters'
            list.seq=5
            list.save()
        
        list, created = EmailList.objects.get_or_create(regex='^(.*)$', handler='UserEmail')
        if created:
            list.description = 'Aliases for all users'
            list.seq = 10
            list.subject_prefix='[%s]' % settings.ORGANIZATION_SHORT_NAME
            list.save()

    def backwards(self, orm):
        pass


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
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
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'dbmail.emaillist': {
            'Meta': {'object_name': 'EmailList'},
            'admin_hold': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'cc_all': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'regex': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'seq': ('django.db.models.fields.PositiveIntegerField', [], {'blank': 'True'}),
            'subject_prefix': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        'dbmail.emailrequest': {
            'Meta': {'object_name': 'EmailRequest'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'msgreq': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dbmail.MessageRequest']"}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'textofemail': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dbmail.TextOfEmail']", 'null': 'True', 'blank': 'True'})
        },
        'dbmail.messagerequest': {
            'Meta': {'object_name': 'MessageRequest'},
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'email_all': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'msgtext': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'priority_level': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'processed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True', 'blank': 'True'}),
            'processed_by': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'db_index': 'True'}),
            'recipients': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.PersistentQueryFilter']"}),
            'sender': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'special_headers': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'dbmail.messagevars': {
            'Meta': {'object_name': 'MessageVars'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'messagerequest': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['dbmail.MessageRequest']"}),
            'pickled_provider': ('django.db.models.fields.TextField', [], {}),
            'provider_name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'dbmail.plainredirect': {
            'Meta': {'object_name': 'PlainRedirect'},
            'destination': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        'dbmail.textofemail': {
            'Meta': {'object_name': 'TextOfEmail'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'msgtext': ('django.db.models.fields.TextField', [], {}),
            'send_from': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'send_to': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'sent': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'sent_by': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.TextField', [], {})
        },
        'users.persistentqueryfilter': {
            'Meta': {'object_name': 'PersistentQueryFilter'},
            'create_ts': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_model': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'q_filter': ('django.db.models.fields.TextField', [], {}),
            'sha1_hash': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'useful_name': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['dbmail']
