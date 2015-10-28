# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from esp.program.modules.models import install

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        # Note: Don't use "from appname.models import ModelName". 
        # Use orm.ModelName to refer to models in this application,
        # and orm['appname.ModelName'] for models in other applications.
        orm.ProgramModuleObj.objects.filter(
            module__handler='SchedulingModule').delete()
        orm['program.ProgramModule'].objects.filter(
            handler='SchedulingModule').delete()

    def backwards(self, orm):
        "Write your backwards methods here."
        install()

    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cal.event': {
            'Meta': {'object_name': 'Event'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cal.EventType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'priority': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']", 'null': 'True', 'blank': 'True'}),
            'short_description': ('django.db.models.fields.TextField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {})
        },
        'cal.eventtype': {
            'Meta': {'object_name': 'EventType'},
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
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
        'modules.ajaxchangelog': {
            'Meta': {'object_name': 'AJAXChangeLog'},
            'entries': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['modules.AJAXChangeLogEntry']", 'symmetrical': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"})
        },
        'modules.ajaxchangelogentry': {
            'Meta': {'object_name': 'AJAXChangeLogEntry'},
            'cls_id': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'index': ('django.db.models.fields.IntegerField', [], {}),
            'room_name': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'time': ('django.db.models.fields.FloatField', [], {}),
            'timeslots': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'modules.classregmoduleinfo': {
            'Meta': {'object_name': 'ClassRegModuleInfo'},
            'allow_coteach': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'allow_lateness': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'allowed_sections': ('django.db.models.fields.CommaSeparatedIntegerField', [], {'max_length': '100', 'blank': 'True'}),
            'ask_for_room': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'class_max_duration': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'class_max_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'class_min_cap': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'class_other_sizes': ('django.db.models.fields.CommaSeparatedIntegerField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'class_size_step': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'color_code': ('django.db.models.fields.CharField', [], {'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['modules.ProgramModuleObj']"}),
            'num_teacher_questions': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'open_class_registration': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'progress_mode': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'session_counts': ('django.db.models.fields.CommaSeparatedIntegerField', [], {'max_length': '100', 'blank': 'True'}),
            'set_prereqs': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_allowable_class_size_ranges': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'use_class_size_max': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'use_class_size_optimal': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'use_optimal_class_size_range': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'modules.dbreceipt': {
            'Meta': {'object_name': 'DBReceipt'},
            'action': ('django.db.models.fields.CharField', [], {'default': "'confirm'", 'max_length': '80'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'receipt': ('django.db.models.fields.TextField', [], {})
        },
        'modules.programmoduleobj': {
            'Meta': {'object_name': 'ProgramModuleObj'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.ProgramModule']"}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'required_label': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'seq': ('django.db.models.fields.IntegerField', [], {})
        },
        'modules.studentclassregmoduleinfo': {
            'Meta': {'object_name': 'StudentClassRegModuleInfo'},
            'apply_multiplier_to_room_cap': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'cancel_button_dereg': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'cancel_button_text': ('django.db.models.fields.CharField', [], {'default': "'Cancel Registration'", 'max_length': '80'}),
            'class_cap_multiplier': ('django.db.models.fields.DecimalField', [], {'default': "'1.00'", 'max_digits': '3', 'decimal_places': '2'}),
            'class_cap_offset': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'confirm_button_text': ('django.db.models.fields.CharField', [], {'default': "'Confirm'", 'max_length': '80'}),
            'enforce_max': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'force_show_required_modules': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['modules.ProgramModuleObj']"}),
            'priority_limit': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'progress_mode': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'register_from_catalog': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'send_confirmation': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'show_emailcodes': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'signup_verb': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.RegistrationType']", 'null': 'True'}),
            'temporarily_full_text': ('django.db.models.fields.CharField', [], {'default': "'Class temporarily full; please check back later'", 'max_length': '255'}),
            'use_grade_range_exceptions': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'use_priority': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'view_button_text': ('django.db.models.fields.CharField', [], {'default': "'View Receipt'", 'max_length': '80'}),
            'visible_enrollments': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'visible_meeting_times': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        },
        'program.archiveclass': {
            'Meta': {'object_name': 'ArchiveClass'},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'date': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_old_students': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'original_id': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'program': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'student_ids': ('django.db.models.fields.TextField', [], {}),
            'teacher': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'teacher_ids': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'year': ('django.db.models.fields.CharField', [], {'max_length': '4'})
        },
        'program.booleanexpression': {
            'Meta': {'object_name': 'BooleanExpression'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'label': ('django.db.models.fields.CharField', [], {'max_length': '80'})
        },
        'program.booleantoken': {
            'Meta': {'object_name': 'BooleanToken'},
            'exp': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.BooleanExpression']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'seq': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'text': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'})
        },
        'program.classcategories': {
            'Meta': {'object_name': 'ClassCategories'},
            'category': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'seq': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'symbol': ('django.db.models.fields.CharField', [], {'default': "'?'", 'max_length': '1'})
        },
        'program.classflag': {
            'Meta': {'ordering': "['flag_type']", 'object_name': 'ClassFlag'},
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'classflags_created'", 'to': "orm['auth.User']"}),
            'created_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'flag_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.ClassFlagType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified_by': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'classflags_modified'", 'to': "orm['auth.User']"}),
            'modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'flags'", 'to': "orm['program.ClassSubject']"})
        },
        'program.classflagtype': {
            'Meta': {'ordering': "['seq']", 'object_name': 'ClassFlagType'},
            'color': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '255'}),
            'seq': ('django.db.models.fields.SmallIntegerField', [], {'default': '0'}),
            'show_in_dashboard': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'show_in_scheduler': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'program.classimplication': {
            'Meta': {'object_name': 'ClassImplication', 'db_table': "'program_classimplications'"},
            'cls': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.ClassSubject']", 'null': 'True'}),
            'enforce': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_prereq': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'member_ids': ('django.db.models.fields.CommaSeparatedIntegerField', [], {'max_length': '100', 'blank': 'True'}),
            'operation': ('django.db.models.fields.CharField', [], {'max_length': '4'}),
            'parent': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': "orm['program.ClassImplication']", 'null': 'True'})
        },
        'program.classsection': {
            'Meta': {'ordering': "['id']", 'object_name': 'ClassSection'},
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']", 'null': 'True', 'blank': 'True'}),
            'checklist_progress': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.ProgramCheckItem']", 'symmetrical': 'False', 'blank': 'True'}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'enrolled_students': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locations': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['resources.Location']", 'symmetrical': 'False', 'blank': 'True'}),
            'max_class_capacity': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'meeting_times': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'meeting_times'", 'blank': 'True', 'to': "orm['cal.Event']"}),
            'parent_class': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'sections'", 'to': "orm['program.ClassSubject']"}),
            'registration_status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'registrations': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'through': "orm['program.StudentRegistration']", 'symmetrical': 'False'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'})
        },
        'program.classsizerange': {
            'Meta': {'object_name': 'ClassSizeRange'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']", 'null': 'True', 'blank': 'True'}),
            'range_max': ('django.db.models.fields.IntegerField', [], {}),
            'range_min': ('django.db.models.fields.IntegerField', [], {})
        },
        'program.classsubject': {
            'Meta': {'object_name': 'ClassSubject', 'db_table': "'program_class'"},
            'allow_lateness': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'allowable_class_size_ranges': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'classsubject_allowedsizes'", 'null': 'True', 'symmetrical': 'False', 'to': "orm['program.ClassSizeRange']"}),
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']", 'null': 'True', 'blank': 'True'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'cls'", 'to': "orm['program.ClassCategories']"}),
            'checklist_progress': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.ProgramCheckItem']", 'symmetrical': 'False', 'blank': 'True'}),
            'class_info': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'class_size_max': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'class_size_min': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'class_size_optimal': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'custom_form_data': ('esp.utils.fields.JSONField', [], {'null': 'True', 'blank': 'True'}),
            'directors_notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'duration': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '5', 'decimal_places': '2', 'blank': 'True'}),
            'grade_max': ('django.db.models.fields.IntegerField', [], {}),
            'grade_min': ('django.db.models.fields.IntegerField', [], {}),
            'hardness_rating': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'meeting_times': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cal.Event']", 'symmetrical': 'False', 'blank': 'True'}),
            'message_for_directors': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'optimal_class_size_range': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.ClassSizeRange']", 'null': 'True', 'blank': 'True'}),
            'parent_program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'prereqs': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'purchase_requests': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requested_room': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'requested_special_resources': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'schedule': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'session_count': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'status': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'teachers': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.User']", 'symmetrical': 'False'}),
            'title': ('django.db.models.fields.TextField', [], {})
        },
        'program.financialaidrequest': {
            'Meta': {'unique_together': "(('program', 'user'),)", 'object_name': 'FinancialAidRequest'},
            'done': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'extra_explaination': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'household_income': ('django.db.models.fields.CharField', [], {'max_length': '12', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'reduced_lunch': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'student_prepare': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'program.program': {
            'Meta': {'object_name': 'Program'},
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']", 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'class_categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.ClassCategories']", 'symmetrical': 'False'}),
            'director_cc_email': ('django.db.models.fields.EmailField', [], {'default': "''", 'max_length': '75', 'blank': 'True'}),
            'director_confidential_email': ('django.db.models.fields.EmailField', [], {'default': "''", 'max_length': '75', 'blank': 'True'}),
            'director_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'flag_types': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.ClassFlagType']", 'symmetrical': 'False', 'blank': 'True'}),
            'grade_max': ('django.db.models.fields.IntegerField', [], {}),
            'grade_min': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80'}),
            'program_allow_waitlist': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'program_modules': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.ProgramModule']", 'symmetrical': 'False'}),
            'program_size_max': ('django.db.models.fields.IntegerField', [], {'null': 'True'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '80'})
        },
        'program.programcheckitem': {
            'Meta': {'ordering': "('seq',)", 'object_name': 'ProgramCheckItem'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'checkitems'", 'to': "orm['program.Program']"}),
            'seq': ('django.db.models.fields.PositiveIntegerField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '512'})
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
        'program.registrationprofile': {
            'Meta': {'object_name': 'RegistrationProfile'},
            'contact_emergency': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'as_emergency'", 'null': 'True', 'to': "orm['users.ContactInfo']"}),
            'contact_guardian': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'as_guardian'", 'null': 'True', 'to': "orm['users.ContactInfo']"}),
            'contact_user': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'as_user'", 'null': 'True', 'to': "orm['users.ContactInfo']"}),
            'educator_info': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'as_educator'", 'null': 'True', 'to': "orm['users.EducatorInfo']"}),
            'email_verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'emailverifycode': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'guardian_info': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'as_guardian'", 'null': 'True', 'to': "orm['users.GuardianInfo']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_ts': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2015, 3, 8, 0, 0)'}),
            'most_recent_profile': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'old_text_reminder': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'db_column': "'text_reminder'", 'blank': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']", 'null': 'True', 'blank': 'True'}),
            'student_info': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'as_student'", 'null': 'True', 'to': "orm['users.StudentInfo']"}),
            'teacher_info': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'as_teacher'", 'null': 'True', 'to': "orm['users.TeacherInfo']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'program.registrationtype': {
            'Meta': {'unique_together': "(('name', 'category'),)", 'object_name': 'RegistrationType'},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'displayName': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'program.scheduleconstraint': {
            'Meta': {'object_name': 'ScheduleConstraint'},
            'condition': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'condition_constraint'", 'to': "orm['program.BooleanExpression']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'on_failure': ('django.db.models.fields.TextField', [], {}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'requirement': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'requirement_constraint'", 'to': "orm['program.BooleanExpression']"})
        },
        'program.scheduletestcategory': {
            'Meta': {'object_name': 'ScheduleTestCategory', '_ormbases': ['program.ScheduleTestTimeblock']},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.ClassCategories']"}),
            'scheduletesttimeblock_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['program.ScheduleTestTimeblock']", 'unique': 'True', 'primary_key': 'True'})
        },
        'program.scheduletestoccupied': {
            'Meta': {'object_name': 'ScheduleTestOccupied', '_ormbases': ['program.ScheduleTestTimeblock']},
            'scheduletesttimeblock_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['program.ScheduleTestTimeblock']", 'unique': 'True', 'primary_key': 'True'})
        },
        'program.scheduletestsectionlist': {
            'Meta': {'object_name': 'ScheduleTestSectionList', '_ormbases': ['program.ScheduleTestTimeblock']},
            'scheduletesttimeblock_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['program.ScheduleTestTimeblock']", 'unique': 'True', 'primary_key': 'True'}),
            'section_ids': ('django.db.models.fields.TextField', [], {})
        },
        'program.scheduletesttimeblock': {
            'Meta': {'object_name': 'ScheduleTestTimeblock', '_ormbases': ['program.BooleanToken']},
            'booleantoken_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['program.BooleanToken']", 'unique': 'True', 'primary_key': 'True'}),
            'timeblock': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cal.Event']"})
        },
        'program.splashinfo': {
            'Meta': {'object_name': 'SplashInfo'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lunchsat': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'lunchsun': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']", 'null': 'True'}),
            'siblingdiscount': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'}),
            'siblingname': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'student': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'submitted': ('django.db.models.fields.NullBooleanField', [], {'default': 'False', 'null': 'True', 'blank': 'True'})
        },
        'program.studentapplication': {
            'Meta': {'object_name': 'StudentApplication', 'db_table': "'program_junctionstudentapp'"},
            'director_score': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'done': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'questions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.StudentAppQuestion']", 'symmetrical': 'False'}),
            'rejected': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'responses': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.StudentAppResponse']", 'symmetrical': 'False'}),
            'reviews': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.StudentAppReview']", 'symmetrical': 'False'}),
            'teacher_score': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'program.studentappquestion': {
            'Meta': {'object_name': 'StudentAppQuestion'},
            'directions': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']", 'null': 'True', 'blank': 'True'}),
            'question': ('django.db.models.fields.TextField', [], {}),
            'subject': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.ClassSubject']", 'null': 'True', 'blank': 'True'})
        },
        'program.studentappresponse': {
            'Meta': {'object_name': 'StudentAppResponse'},
            'complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'question': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.StudentAppQuestion']"}),
            'response': ('django.db.models.fields.TextField', [], {'default': "''"})
        },
        'program.studentappreview': {
            'Meta': {'object_name': 'StudentAppReview'},
            'comments': ('django.db.models.fields.TextField', [], {}),
            'date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reject': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'reviewer': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"}),
            'score': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'program.studentregistration': {
            'Meta': {'object_name': 'StudentRegistration'},
            'end_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'relationship': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.RegistrationType']"}),
            'section': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.ClassSection']"}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'program.studentsubjectinterest': {
            'Meta': {'object_name': 'StudentSubjectInterest'},
            'end_date': ('django.db.models.fields.DateTimeField', [], {'default': 'None', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start_date': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now', 'null': 'True', 'blank': 'True'}),
            'subject': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.ClassSubject']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'program.teacherbio': {
            'Meta': {'object_name': 'TeacherBio'},
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'hidden': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_ts': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'picture': ('django.db.models.fields.files.ImageField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'picture_height': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'picture_width': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']", 'null': 'True', 'blank': 'True'}),
            'slugbio': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        },
        'program.volunteeroffer': {
            'Meta': {'object_name': 'VolunteerOffer'},
            'comments': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'confirmed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '80', 'null': 'True', 'blank': 'True'}),
            'phone': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'request': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.VolunteerRequest']"}),
            'shirt_size': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'shirt_type': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'program.volunteerrequest': {
            'Meta': {'object_name': 'VolunteerRequest'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_volunteers': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'timeslot': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cal.Event']"})
        },
        'qsdmedia.media': {
            'Meta': {'object_name': 'Media'},
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']", 'null': 'True', 'blank': 'True'}),
            'file_extension': ('django.db.models.fields.TextField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'file_name': ('django.db.models.fields.TextField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'format': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'friendly_name': ('django.db.models.fields.TextField', [], {}),
            'hashed_name': ('django.db.models.fields.TextField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mime_type': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'owner_id': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'owner_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']", 'null': 'True', 'blank': 'True'}),
            'size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'target_file': ('django.db.models.fields.files.FileField', [], {'max_length': '100'})
        },
        'resources.location': {
            'Meta': {'object_name': 'Location'},
            'admin_notes': ('django.db.models.fields.TextField', [], {}),
            'capacity': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'student_notes': ('django.db.models.fields.TextField', [], {}),
            'teacher_notes': ('django.db.models.fields.TextField', [], {})
        },
        'users.contactinfo': {
            'Meta': {'object_name': 'ContactInfo'},
            'address_city': ('django.db.models.fields.CharField', [], {'max_length': '50', 'null': 'True', 'blank': 'True'}),
            'address_postal': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'address_state': ('django.contrib.localflavor.us.models.USStateField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            'address_street': ('django.db.models.fields.CharField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'address_zip': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'e_mail': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'phone_cell': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'phone_day': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'phone_even': ('django.contrib.localflavor.us.models.PhoneNumberField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'receive_txt_message': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'undeliverable': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'users.educatorinfo': {
            'Meta': {'object_name': 'EducatorInfo'},
            'grades_taught': ('django.db.models.fields.CharField', [], {'max_length': '16', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'k12school': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.K12School']", 'null': 'True', 'blank': 'True'}),
            'position': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'school': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'subject_taught': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'users.guardianinfo': {
            'Meta': {'object_name': 'GuardianInfo'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'num_kids': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'year_finished': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'users.k12school': {
            'Meta': {'object_name': 'K12School'},
            'contact': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.ContactInfo']", 'null': 'True', 'blank': 'True'}),
            'contact_title': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'grades': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'school_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'school_type': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        'users.studentinfo': {
            'Meta': {'object_name': 'StudentInfo'},
            'dob': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'food_preference': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'gender': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'graduation_year': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'heard_about': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'k12school': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['users.K12School']", 'null': 'True', 'blank': 'True'}),
            'medical_needs': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'post_hs': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'school': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'schoolsystem_id': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'schoolsystem_optout': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'shirt_size': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'shirt_type': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'studentrep': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'studentrep_expl': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'transportation': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'users.teacherinfo': {
            'Meta': {'object_name': 'TeacherInfo'},
            'bio': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'college': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'from_here': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'full_legal_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'graduation_year': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_graduate_student': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'mail_reimbursement': ('django.db.models.fields.NullBooleanField', [], {'null': 'True', 'blank': 'True'}),
            'major': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'shirt_size': ('django.db.models.fields.CharField', [], {'max_length': '5', 'null': 'True', 'blank': 'True'}),
            'shirt_type': ('django.db.models.fields.CharField', [], {'max_length': '20', 'null': 'True', 'blank': 'True'}),
            'student_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'university_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['program', 'modules']
    symmetrical = True
