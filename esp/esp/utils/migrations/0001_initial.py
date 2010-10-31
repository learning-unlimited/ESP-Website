# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'TemplateOverride'
        db.create_table('utils_templateoverride', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('content', self.gf('django.db.models.fields.TextField')()),
            ('version', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('utils', ['TemplateOverride'])

        # Adding unique constraint on 'TemplateOverride', fields ['name', 'version']
        db.create_unique('utils_templateoverride', ['name', 'version'])


    def backwards(self, orm):
        
        # Deleting model 'TemplateOverride'
        db.delete_table('utils_templateoverride')

        # Removing unique constraint on 'TemplateOverride', fields ['name', 'version']
        db.delete_unique('utils_templateoverride', ['name', 'version'])


    models = {
        'utils.templateoverride': {
            'Meta': {'unique_together': "(('name', 'version'),)", 'object_name': 'TemplateOverride'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'version': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['utils']
