
from south.db import db
from django.db import models
from esp.program.modules.models import *

class Migration:

    def forwards(self, orm):
        
        # Adding field 'StudentClassRegModuleInfo.force_show_required_modules'
        db.add_column('modules_studentclassregmoduleinfo', 'force_show_required_modules', orm['modules.studentclassregmoduleinfo:force_show_required_modules'])
        
    
    
    def backwards(self, orm):
        
        # Deleting field 'StudentClassRegModuleInfo.force_show_required_modules'
        db.delete_column('modules_studentclassregmoduleinfo', 'force_show_required_modules')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'cal.event': {
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']"}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cal.EventType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'priority': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'short_description': ('django.db.models.fields.TextField', [], {}),
            'start': ('django.db.models.fields.DateTimeField', [], {})
        },
        'cal.eventtype': {
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'datatree.datatree': {
            'Meta': {'unique_together': "(('name', 'parent'),)"},
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
        },
        'modules.classregmoduleinfo': {
            'allow_coteach': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'allow_lateness': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'allowed_sections': ('django.db.models.fields.CommaSeparatedIntegerField', [], {'max_length': '100', 'blank': 'True'}),
            'ask_for_room': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'class_durations': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'class_max_duration': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'class_max_size': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'class_size_step': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'color_code': ('django.db.models.fields.CharField', [], {'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'director_email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'null': 'True', 'blank': 'True'}),
            'display_times': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['modules.ProgramModuleObj']"}),
            'num_class_choices': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'num_teacher_questions': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'progress_mode': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'session_counts': ('django.db.models.fields.CommaSeparatedIntegerField', [], {'max_length': '100', 'blank': 'True'}),
            'set_prereqs': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'teacher_class_noedit': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'times_selectmultiple': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'})
        },
        'modules.creditcardmoduleinfo': {
            'base_cost': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['modules.ProgramModuleObj']"})
        },
        'modules.dbreceipt': {
            'action': ('django.db.models.fields.CharField', [], {'default': "'confirm'", 'max_length': '80'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'receipt': ('django.db.models.fields.TextField', [], {})
        },
        'modules.programmoduleobj': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.ProgramModule']"}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'seq': ('django.db.models.fields.IntegerField', [], {})
        },
        'modules.remoteprofile': {
            'bus_runs': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['datatree.DataTree']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'need_bus': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'volunteer': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'volunteer_times': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['cal.Event']", 'blank': 'True'})
        },
        'modules.satprepadminmoduleinfo': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['modules.ProgramModuleObj']"}),
            'num_divisions': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'})
        },
        'modules.satprepteachermoduleinfo': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mitid': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']", 'null': 'True', 'blank': 'True'}),
            'sat_math': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sat_verb': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'sat_writ': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'section': ('django.db.models.fields.CharField', [], {'max_length': '5'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'modules.studentclassregmoduleinfo': {
            'cancel_button_dereg': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'cancel_button_text': ('django.db.models.fields.CharField', [], {'default': "'Cancel Registration'", 'max_length': '80'}),
            'class_cap_multiplier': ('django.db.models.fields.DecimalField', [], {'default': "'1.00'", 'max_digits': '3', 'decimal_places': '2'}),
            'class_cap_offset': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'confirm_button_text': ('django.db.models.fields.CharField', [], {'default': "'Confirm'", 'max_length': '80'}),
            'enforce_max': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'force_show_required_modules': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['modules.ProgramModuleObj']"}),
            'priority_limit': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'progress_mode': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'register_from_catalog': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'send_confirmation': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'show_emailcodes': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'show_unscheduled_classes': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'signup_verb': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']"}),
            'temporarily_full_text': ('django.db.models.fields.CharField', [], {'default': "'Class temporarily full; please check back later'", 'max_length': '255'}),
            'use_priority': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'view_button_text': ('django.db.models.fields.CharField', [], {'default': "'View Receipt'", 'max_length': '80'}),
            'visible_enrollments': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'visible_meeting_times': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'})
        },
        'program.classcategories': {
            'category': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'symbol': ('django.db.models.fields.CharField', [], {'default': "'?'", 'max_length': '1'})
        },
        'program.program': {
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']"}),
            'class_categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.ClassCategories']"}),
            'class_size_max': ('django.db.models.fields.IntegerField', [], {}),
            'class_size_min': ('django.db.models.fields.IntegerField', [], {}),
            'director_email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'grade_max': ('django.db.models.fields.IntegerField', [], {}),
            'grade_min': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'program_allow_waitlist': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'program_modules': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['program.ProgramModule']"}),
            'program_size_max': ('django.db.models.fields.IntegerField', [], {'null': 'True'})
        },
        'program.programmodule': {
            'admin_title': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'aux_calls': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'handler': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'link_title': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'main_call': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'module_type': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'seq': ('django.db.models.fields.IntegerField', [], {}),
            'summary_calls': ('django.db.models.fields.CharField', [], {'max_length': '512', 'null': 'True', 'blank': 'True'})
        }
    }
    
    complete_apps = ['modules']
