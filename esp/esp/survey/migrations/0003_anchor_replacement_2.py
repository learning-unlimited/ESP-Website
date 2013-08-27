# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from django.core.exceptions import MultipleObjectsReturned
from django.contrib.contenttypes.models import ContentType
from esp.program.models import Program, ClassSubject, ClassSection
from esp.survey.models import Survey, Question, Answer

class Migration(DataMigration):

    depends_on = ( ("program", "0034_class_program_datamigrations"), )

    def forwards(self, orm):

        #survey model
        for s in orm.Survey.objects.all():
            p=orm['program.Program'].objects.get(anchor=s.anchor)
            s.program=p
            s.save()

        #question model
        for q in orm.Question.objects.all():
            if q.anchor.name == 'Classes':
                q.per_class = True
                q.save()

        ##  Rather than updating each answer with a separate query, we'll update
        ##  them in batches for each target object they're associated to.  There
        ##  are less programs, class subjects, and class sections than there are
        ##  answers.

        #   Find answers associated with programs
        program_ct = ContentType.objects.get(app_label='program', model='program')
        for program in Program.objects.all():
            orm.Answer.objects.filter(anchor=program.anchor).update(object_id=program.id, content_type=program_ct)
        print 'Updated %d programs' % Program.objects.all().count()
        
        #   Find answers associated with class subjects
        subject_ct = ContentType.objects.get(app_label='program', model='classsubject')
        print 'Need to update %d class subjects' % ClassSubject.objects.all().count()
        N = 0
        for subject in ClassSubject.objects.all():
            orm.Answer.objects.filter(anchor=subject.anchor).update(object_id=subject.id, content_type=subject_ct)
            N += 1
            if N % 500 == 0:
                print '-- Updated %d class subjects' % N

        #   Find answers associated with class sections
        section_ct = ContentType.objects.get(app_label='program', model='classsection')
        print 'Need to update %d class sections' % ClassSection.objects.all().count()
        N = 0
        for section in ClassSection.objects.all():
            try:
                orm.Answer.objects.filter(anchor=section.anchor).update(object_id=section.id, content_type=section_ct)
            except:
                print 'Section without valid anchor: %s' % section
            N += 1
            if N % 500 == 0:
                print '-- Updated %d class sections' % N

    def backwards(self, orm):
        "Write your backwards methods here."
        raise RuntimeError
    
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
        'program.classcategories': {
            'Meta': {'object_name': 'ClassCategories'},
            'category': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'seq': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'symbol': ('django.db.models.fields.CharField', [], {'default': "'?'", 'max_length': '1'})
        },
        'program.program': {
            'Meta': {'object_name': 'Program'},
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']", 'unique': 'True'}),
            'class_categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.ClassCategories']", 'symmetrical': 'False'}),
            'director_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'grade_max': ('django.db.models.fields.IntegerField', [], {}),
            'grade_min': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'program_allow_waitlist': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'program_modules': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.ProgramModule']", 'symmetrical': 'False'}),
            'program_size_max': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '80'})
        },
        'program.programmodule': {
            'Meta': {'object_name': 'ProgramModule'},
            'admin_title': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'handler': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'inline_template': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'link_title': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'module_type': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'seq': ('django.db.models.fields.IntegerField', [], {})
        },
        'survey.answer': {
            'Meta': {'object_name': 'Answer'},
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']"}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
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
            'per_class': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'surveys'", 'null': 'True', 'to': "orm['program.Program']"})
        },
        'survey.surveyresponse': {
            'Meta': {'object_name': 'SurveyResponse'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'survey': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['survey.Survey']"}),
            'time_filled': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'})
        }
    }

    complete_apps = ['survey']
