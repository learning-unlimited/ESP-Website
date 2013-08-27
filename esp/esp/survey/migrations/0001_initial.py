# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Survey'
        db.create_table('survey_survey', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('anchor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='surveys', to=orm['datatree.DataTree'])),
            ('category', self.gf('django.db.models.fields.CharField')(max_length=32)),
        ))
        db.send_create_signal('survey', ['Survey'])

        # Adding model 'SurveyResponse'
        db.create_table('survey_surveyresponse', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('time_filled', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime.now)),
            ('survey', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['survey.Survey'])),
        ))
        db.send_create_signal('survey', ['SurveyResponse'])

        # Adding model 'QuestionType'
        db.create_table('survey_questiontype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('_param_names', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('is_numeric', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('is_countable', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('survey', ['QuestionType'])

        # Adding model 'Question'
        db.create_table('survey_question', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('survey', self.gf('django.db.models.fields.related.ForeignKey')(related_name='questions', to=orm['survey.Survey'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('question_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['survey.QuestionType'])),
            ('_param_values', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('anchor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='questions', to=orm['datatree.DataTree'])),
            ('seq', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('survey', ['Question'])

        # Adding model 'Answer'
        db.create_table('survey_answer', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('survey_response', self.gf('django.db.models.fields.related.ForeignKey')(related_name='answers', to=orm['survey.SurveyResponse'])),
            ('anchor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['datatree.DataTree'])),
            ('question', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['survey.Question'])),
            ('value', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('survey', ['Answer'])


    def backwards(self, orm):
        
        # Deleting model 'Survey'
        db.delete_table('survey_survey')

        # Deleting model 'SurveyResponse'
        db.delete_table('survey_surveyresponse')

        # Deleting model 'QuestionType'
        db.delete_table('survey_questiontype')

        # Deleting model 'Question'
        db.delete_table('survey_question')

        # Deleting model 'Answer'
        db.delete_table('survey_answer')


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
        'survey.answer': {
            'Meta': {'object_name': 'Answer'},
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['survey.Question']"}),
            'survey_response': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'answers'", 'to': "orm['survey.SurveyResponse']"}),
            'value': ('django.db.models.fields.TextField', [], {})
        },
        'survey.question': {
            'Meta': {'ordering': "['seq']", 'object_name': 'Question'},
            '_param_values': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'questions'", 'to': "orm['datatree.DataTree']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'question_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['survey.QuestionType']"}),
            'seq': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'survey': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'questions'", 'to': "orm['survey.Survey']"})
        },
        'survey.questiontype': {
            'Meta': {'object_name': 'QuestionType'},
            '_param_names': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_countable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_numeric': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'survey.survey': {
            'Meta': {'object_name': 'Survey'},
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'surveys'", 'to': "orm['datatree.DataTree']"}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'survey.surveyresponse': {
            'Meta': {'object_name': 'SurveyResponse'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'survey': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['survey.Survey']"}),
            'time_filled': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        }
    }

    complete_apps = ['survey']
