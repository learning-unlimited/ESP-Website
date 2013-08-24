# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

from esp.datatree.models import DataTree, GetNode

class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'Entry', fields ['slug', 'anchor']
        # [This doesn't seem to be in all of our production databases. -Michael]
        # db.delete_unique('miniblog_entry', ['slug', 'anchor_id'])

        # Delete all announcements/entries that were not anchored on Q/Web
        # since those anchor points now have no meaning
        try:
            web_node_id = GetNode('Q/Web').id
        except DataTree.DoesNotExist:
            #   If there is no DataTree, delete everything.
            web_node_id = -1
        db.execute('DELETE FROM "miniblog_announcementlink" WHERE "anchor_id" != %s', [web_node_id,])
        db.execute('DELETE FROM "miniblog_entry" WHERE "anchor_id" != %s', [web_node_id,])

        # Deleting field 'AnnouncementLink.anchor'
        db.delete_column('miniblog_announcementlink', 'anchor_id')

        # Deleting field 'Entry.anchor'
        db.delete_column('miniblog_entry', 'anchor_id')


    def backwards(self, orm):
        # Adding field 'AnnouncementLink.anchor'
        db.add_column('miniblog_announcementlink', 'anchor',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['datatree.DataTree']),
                      keep_default=False)

        # Adding field 'Entry.anchor'
        db.add_column('miniblog_entry', 'anchor',
                      self.gf('django.db.models.fields.related.ForeignKey')(default=1, to=orm['datatree.DataTree']),
                      keep_default=False)

        # Set AnnouncementLink and Entry anchors to Q/Web
        web_node = GetNode('Q/Web')
        orm['miniblog.AnnouncementLink'].objects.all().update(anchor=web_node)
        orm['miniblog.Entry'].objects.all().update(anchor=web_node)

        # Adding unique constraint on 'Entry', fields ['slug', 'anchor']
        # db.create_unique('miniblog_entry', ['slug', 'anchor_id'])


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
        'miniblog.announcementlink': {
            'Meta': {'object_name': 'AnnouncementLink'},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'highlight_begin': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'highlight_expire': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'href': ('django.db.models.fields.URLField', [], {'max_length': '200'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'section': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'miniblog.comment': {
            'Meta': {'ordering': "['-post_ts']", 'object_name': 'Comment'},
            'author': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'content': ('django.db.models.fields.TextField', [], {}),
            'entry': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['miniblog.Entry']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'post_ts': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        },
        'miniblog.entry': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Entry'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'email': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'fromemail': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'fromuser': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'highlight_begin': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'highlight_expire': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'section': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'sent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'slug': ('django.db.models.fields.SlugField', [], {'default': "'General'", 'max_length': '50'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        }
    }

    complete_apps = ['miniblog']