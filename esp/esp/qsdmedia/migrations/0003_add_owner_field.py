# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Media.owner_type'
        db.add_column('qsdmedia_media', 'owner_type',
                      self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'], null=True, blank=True),
                      keep_default=False)

        # Adding field 'Media.owner_id'
        db.add_column('qsdmedia_media', 'owner_id',
                      self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True),
                      keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Media.owner_type'
        db.delete_column('qsdmedia_media', 'owner_type_id')

        # Deleting field 'Media.owner_id'
        db.delete_column('qsdmedia_media', 'owner_id')


    models = {
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'datatree.datatree': {
            'Meta': {'unique_together': "(('name', 'parent'),)", 'object_name': 'DataTree'},
            'friendly_name': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lock_table': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'child_set'", 'null': 'True', 'to': "orm['datatree.DataTree']"}),
            'range_correct': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'rangeend': ('django.db.models.fields.IntegerField', [], {}),
            'rangestart': ('django.db.models.fields.IntegerField', [], {}),
            'uri': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'uri_correct': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'qsdmedia.media': {
            'Meta': {'object_name': 'Media'},
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']", 'null': 'True', 'blank': 'True'}),
            'file_extension': ('django.db.models.fields.TextField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'format': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'friendly_name': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mime_type': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'owner_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'owner_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'target_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'})
        },
        'qsdmedia.paper': {
            'Meta': {'object_name': 'Paper'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_mutable_text': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'media': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['qsdmedia.Media']", 'unique': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['qsdmedia.PaperType']"})
        },
        'qsdmedia.papertype': {
            'Meta': {'object_name': 'PaperType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type_description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'qsdmedia.picture': {
            'Meta': {'object_name': 'Picture'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_arbitrarily_resizable_format': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'media': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['qsdmedia.Media']", 'unique': 'True'}),
            'x_resolution': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'y_resolution': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'qsdmedia.video': {
            'Meta': {'object_name': 'Video'},
            'audio_codec': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'bitrate': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'container_format': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'duration': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'media': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['qsdmedia.Media']", 'unique': 'True'}),
            'video_codec': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['qsdmedia']