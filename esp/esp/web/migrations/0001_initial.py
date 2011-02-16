# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'NavBarCategory'
        db.create_table('web_navbarcategory', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('anchor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['datatree.DataTree'], null=True, blank=True)),
            ('include_auto_links', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('long_explanation', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('web', ['NavBarCategory'])

        # Adding model 'NavBarEntry'
        db.create_table('web_navbarentry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('path', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='navbar', null=True, to=orm['datatree.DataTree'])),
            ('sort_rank', self.gf('django.db.models.fields.IntegerField')()),
            ('link', self.gf('django.db.models.fields.CharField')(max_length=256, null=True, blank=True)),
            ('text', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('indent', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['web.NavBarCategory'])),
        ))
        db.send_create_signal('web', ['NavBarEntry'])


    def backwards(self, orm):
        
        # Deleting model 'NavBarCategory'
        db.delete_table('web_navbarcategory')

        # Deleting model 'NavBarEntry'
        db.delete_table('web_navbarentry')


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
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'web.navbarentry': {
            'Meta': {'object_name': 'NavBarEntry'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['web.NavBarCategory']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'indent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'link': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'path': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'navbar'", 'null': 'True', 'to': "orm['datatree.DataTree']"}),
            'sort_rank': ('django.db.models.fields.IntegerField', [], {}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        }
    }

    complete_apps = ['web']
