# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'MyUser'
        db.create_table('customforms_myuser', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(default='User', max_length=15)),
        ))
        db.send_create_signal('customforms', ['MyUser'])

        # Adding model 'Form'
        db.create_table('customforms_form', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('title', self.gf('django.db.models.fields.CharField')(default='Form', max_length=30)),
            ('active', self.gf('django.db.models.fields.IntegerField')(default=1, max_length=2)),
        ))
        db.send_create_signal('customforms', ['Form'])

        # Adding model 'Question'
        db.create_table('customforms_question', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('form', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['customforms.Form'])),
            ('question', self.gf('django.db.models.fields.CharField')(max_length=60)),
            ('ques_type', self.gf('django.db.models.fields.CharField')(max_length=15)),
            ('required', self.gf('django.db.models.fields.CharField')(max_length=2)),
        ))
        db.send_create_signal('customforms', ['Question'])

        # Adding model 'Option'
        db.create_table('customforms_option', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('form', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['customforms.Form'])),
            ('question', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['customforms.Question'])),
            ('opt', self.gf('django.db.models.fields.CharField')(max_length=30)),
        ))
        db.send_create_signal('customforms', ['Option'])

        # Adding model 'Responses'
        db.create_table('customforms_responses', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('question', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['customforms.Question'])),
            ('resp', self.gf('django.db.models.fields.CharField')(max_length=50, null=True, blank=True)),
            ('form', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['customforms.Form'])),
            ('myuser', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['customforms.MyUser'])),
        ))
        db.send_create_signal('customforms', ['Responses'])


    def backwards(self, orm):
        
        # Deleting model 'MyUser'
        db.delete_table('customforms_myuser')

        # Deleting model 'Form'
        db.delete_table('customforms_form')

        # Deleting model 'Question'
        db.delete_table('customforms_question')

        # Deleting model 'Option'
        db.delete_table('customforms_option')

        # Deleting model 'Responses'
        db.delete_table('customforms_responses')


    models = {
        'customforms.form': {
            'Meta': {'object_name': 'Form'},
            'active': ('django.db.models.fields.IntegerField', [], {'default': '1', 'max_length': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'default': "'Form'", 'max_length': '30'})
        },
        'customforms.myuser': {
            'Meta': {'object_name': 'MyUser'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'default': "'User'", 'max_length': '15'})
        },
        'customforms.option': {
            'Meta': {'object_name': 'Option'},
            'form': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['customforms.Form']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'opt': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['customforms.Question']"})
        },
        'customforms.question': {
            'Meta': {'object_name': 'Question'},
            'form': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['customforms.Form']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ques_type': ('django.db.models.fields.CharField', [], {'max_length': '15'}),
            'question': ('django.db.models.fields.CharField', [], {'max_length': '60'}),
            'required': ('django.db.models.fields.CharField', [], {'max_length': '2'})
        },
        'customforms.responses': {
            'Meta': {'object_name': 'Responses'},
            'form': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['customforms.Form']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'myuser': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['customforms.MyUser']"}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['customforms.Question']"}),
            'resp': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['customforms']
