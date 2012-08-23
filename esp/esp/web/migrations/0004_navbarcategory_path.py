# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models


class Migration(DataMigration):

    def forwards(self, orm):
        
        # Adding field 'NavBarCategory.path'
        db.add_column('web_navbarcategory', 'path', self.gf('django.db.models.fields.CharField')(default='', max_length=128), keep_default=False)

        for navcat in orm.NavBarCategory.objects.all():
            navcat.path = navcat.anchor.uri
            navcat.save()

    def backwards(self, orm):
        
        # Deleting field 'NavBarCategory.path'
        db.delete_column('web_navbarcategory', 'path')

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
        'web.navbarcategory': {
            'Meta': {'object_name': 'NavBarCategory'},
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'include_auto_links': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'long_explanation': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'web.navbarentry': {
            'Meta': {'object_name': 'NavBarEntry'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['web.NavBarCategory']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'indent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'link': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'path': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'navbar'", 'null': 'True', 'to': "orm['datatree.DataTree']"}),
            'sort_rank': ('django.db.models.fields.IntegerField', [], {}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        }
    }

    complete_apps = ['web']
