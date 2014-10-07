# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from django.conf import settings
from django.core.files import File
from esp.qsdmedia.models import Media
import os
import os.path

class Migration(SchemaMigration):

    def forwards(self, orm):
        medias = Media.objects.filter(hashed_name__isnull=True)
        num_converted = 0
        for media in medias:
            full_path = os.path.join(settings.MEDIA_ROOT, '..' + media.target_file.url)
            if os.path.exists(full_path):
                file_name = os.path.basename(media.target_file.url)
                media.hashed_name = media.safe_filename(file_name)
                full_path_new = os.path.join(os.path.dirname(full_path), media.hashed_name)
                os.rename(full_path, full_path_new)
                media.file_name = file_name
                media.target_file.name = os.path.dirname(media.target_file.name) + '/' + media.hashed_name
                media.save()
                print 'Converted %s to %s' % (full_path, media.target_file.url)
                num_converted += 1
            else:
                print 'Skipped %s, file not present on system' % full_path
        print 'Converted %d/%d Media objects to hashed names' % (num_converted, len(medias))

    def backwards(self, orm):
        medias = Media.objects.filter(hashed_name__isnull=False)
        num_converted = 0
        for media in medias:
            full_path = os.path.join(settings.MEDIA_ROOT, '..' + media.target_file.url)
            if os.path.exists(full_path):
                full_path_new = os.path.join(os.path.dirname(full_path), media.file_name)
                media.target_file.name = os.path.dirname(media.target_file.name) + '/' + media.file_name
                os.rename(full_path, full_path_new)
                media.file_name = None
                media.hashed_name = None
                media.save()
                print 'Converted %s to %s' % (full_path, media.target_file.url)
                num_converted += 1
            else:
                print 'Skipped %s, file not present on system' % full_path
        print 'Converted %d/%d Media objects to plaintext names' % (num_converted, len(medias))

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
            'file_name': ('django.db.models.fields.TextField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'format': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'friendly_name': ('django.db.models.fields.TextField', [], {}),
            'hashed_name': ('django.db.models.fields.TextField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
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