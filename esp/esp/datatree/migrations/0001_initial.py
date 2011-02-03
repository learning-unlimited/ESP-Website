# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models
from esp.datatree.models import install as datatree_install

class Migration(SchemaMigration):

    def forwards(self, orm):

        # Adding model 'DataTree'
        db.create_table('datatree_datatree', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('friendly_name', self.gf('django.db.models.fields.TextField')()),
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='child_set', null=True, to=orm['datatree.DataTree'])),
            ('rangestart', self.gf('django.db.models.fields.IntegerField')()),
            ('rangeend', self.gf('django.db.models.fields.IntegerField')()),
            ('uri', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('uri_correct', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('lock_table', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('range_correct', self.gf('django.db.models.fields.BooleanField')(default=True, blank=True)),
        ))
        db.send_create_signal('datatree', ['DataTree'])

        # Adding unique constraint on 'DataTree', fields ['name', 'parent']
        db.create_unique('datatree_datatree', ['name', 'parent_id'])

        #   Force instantiation of datatree initial data if it wasn't already there
        print 'Populating initial datatree...'
        datatree_install()

    def backwards(self, orm):
        
        # Deleting model 'DataTree'
        db.delete_table('datatree_datatree')

        # Removing unique constraint on 'DataTree', fields ['name', 'parent']
        db.delete_unique('datatree_datatree', ['name', 'parent_id'])


    models = {
        'datatree.datatree': {
            'Meta': {'unique_together': "(('name', 'parent'),)", 'object_name': 'DataTree'},
            'friendly_name': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lock_table': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'child_set'", 'null': 'True', 'to': "orm['datatree.DataTree']"}),
            'range_correct': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'rangeend': ('django.db.models.fields.IntegerField', [], {}),
            'rangestart': ('django.db.models.fields.IntegerField', [], {}),
            'uri': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'uri_correct': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'})
        }
    }

    complete_apps = ['datatree']
