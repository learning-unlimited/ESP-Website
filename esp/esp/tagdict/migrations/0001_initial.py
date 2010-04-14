
from south.db import db
from django.db import models
from esp.tagdict.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'Tag'
        db.create_table('tagdict_tag', (
            ('id', orm['tagdict.Tag:id']),
            ('key', orm['tagdict.Tag:key']),
            ('value', orm['tagdict.Tag:value']),
            ('content_type', orm['tagdict.Tag:content_type']),
            ('object_id', orm['tagdict.Tag:object_id']),
        ))
        db.send_create_signal('tagdict', ['Tag'])
        
        # Creating unique_together for [key, content_type, object_id] on Tag.
        db.create_unique('tagdict_tag', ['key', 'content_type_id', 'object_id'])
        
    
    
    def backwards(self, orm):
        
        # Deleting unique_together for [key, content_type, object_id] on Tag.
        db.delete_unique('tagdict_tag', ['key', 'content_type_id', 'object_id'])
        
        # Deleting model 'Tag'
        db.delete_table('tagdict_tag')
        
    
    
    models = {
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'tagdict.tag': {
            'Meta': {'unique_together': "(('key', 'content_type', 'object_id'),)"},
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'db_index': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'value': ('django.db.models.fields.TextField', [], {})
        }
    }
    
    complete_apps = ['tagdict']
