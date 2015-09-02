# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'MessageRequest.email_all'
        db.delete_column(u'dbmail_messagerequest', 'email_all')


    def backwards(self, orm):
        # Adding field 'MessageRequest.email_all'
        db.add_column(u'dbmail_messagerequest', 'email_all',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'dbmail.emaillist': {
            'Meta': {'ordering': "('seq',)", 'object_name': 'EmailList'},
            'admin_hold': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'cc_all': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'regex': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'seq': ('django.db.models.fields.PositiveIntegerField', [], {'blank': 'True'}),
            'subject_prefix': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'})
        },
        u'dbmail.emailrequest': {
            'Meta': {'object_name': 'EmailRequest'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'msgreq': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dbmail.MessageRequest']"}),
            'target': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'textofemail': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dbmail.TextOfEmail']", 'null': 'True', 'blank': 'True'})
        },
        u'dbmail.messagerequest': {
            'Meta': {'object_name': 'MessageRequest'},
            'creator': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'msgtext': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'priority_level': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'processed': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'db_index': 'True'}),
            'processed_by': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'db_index': 'True'}),
            'recipients': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.PersistentQueryFilter']"}),
            'sender': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'sendto_fn_name': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '128'}),
            'special_headers': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'dbmail.messagevars': {
            'Meta': {'object_name': 'MessageVars'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'messagerequest': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['dbmail.MessageRequest']"}),
            'pickled_provider': ('django.db.models.fields.TextField', [], {}),
            'provider_name': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'dbmail.plainredirect': {
            'Meta': {'ordering': "('original',)", 'object_name': 'PlainRedirect'},
            'destination': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'original': ('django.db.models.fields.CharField', [], {'max_length': '512'})
        },
        u'dbmail.textofemail': {
            'Meta': {'object_name': 'TextOfEmail'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'msgtext': ('django.db.models.fields.TextField', [], {}),
            'send_from': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'send_to': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'sent': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'sent_by': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'db_index': 'True'}),
            'subject': ('django.db.models.fields.TextField', [], {}),
            'tries': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'users.persistentqueryfilter': {
            'Meta': {'object_name': 'PersistentQueryFilter'},
            'create_ts': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'item_model': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'q_filter': ('django.db.models.fields.TextField', [], {}),
            'sha1_hash': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'useful_name': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['dbmail']