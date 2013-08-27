import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Media'
        db.create_table('qsdmedia_media', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('anchor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['datatree.DataTree'])),
            ('friendly_name', self.gf('django.db.models.fields.TextField')()),
            ('target_file', self.gf('django.db.models.fields.files.FileField')(max_length=100)),
            ('size', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('format', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('mime_type', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('file_extension', self.gf('django.db.models.fields.TextField')(max_length=16, null=True, blank=True)),
        ))
        db.send_create_signal('qsdmedia', ['Media'])

        # Adding model 'Video'
        db.create_table('qsdmedia_video', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('media', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['qsdmedia.Media'], unique=True)),
            ('container_format', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('audio_codec', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('video_codec', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('bitrate', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('duration', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('qsdmedia', ['Video'])

        # Adding model 'Picture'
        db.create_table('qsdmedia_picture', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('media', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['qsdmedia.Media'], unique=True)),
            ('is_arbitrarily_resizable_format', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('x_resolution', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('y_resolution', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
        ))
        db.send_create_signal('qsdmedia', ['Picture'])

        # Adding model 'PaperType'
        db.create_table('qsdmedia_papertype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type_description', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal('qsdmedia', ['PaperType'])

        # Adding model 'Paper'
        db.create_table('qsdmedia_paper', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('is_mutable_text', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['qsdmedia.PaperType'])),
            ('media', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['qsdmedia.Media'], unique=True)),
        ))
        db.send_create_signal('qsdmedia', ['Paper'])


    def backwards(self, orm):
        # Deleting model 'Media'
        db.delete_table('qsdmedia_media')

        # Deleting model 'Video'
        db.delete_table('qsdmedia_video')

        # Deleting model 'Picture'
        db.delete_table('qsdmedia_picture')

        # Deleting model 'PaperType'
        db.delete_table('qsdmedia_papertype')

        # Deleting model 'Paper'
        db.delete_table('qsdmedia_paper')


    models = {
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
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']"}),
            'file_extension': ('django.db.models.fields.TextField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'format': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'friendly_name': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mime_type': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
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

