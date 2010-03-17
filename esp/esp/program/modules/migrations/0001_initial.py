
from south.db import db
from django.db import models
from esp.program.modules.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'StudentClassRegModuleInfo'
        db.create_table('modules_studentclassregmoduleinfo', (
            ('id', orm['modules.StudentClassRegModuleInfo:id']),
            ('module', orm['modules.StudentClassRegModuleInfo:module']),
            ('enforce_max', orm['modules.StudentClassRegModuleInfo:enforce_max']),
            ('class_cap_multiplier', orm['modules.StudentClassRegModuleInfo:class_cap_multiplier']),
            ('class_cap_offset', orm['modules.StudentClassRegModuleInfo:class_cap_offset']),
            ('signup_verb', orm['modules.StudentClassRegModuleInfo:signup_verb']),
            ('use_priority', orm['modules.StudentClassRegModuleInfo:use_priority']),
            ('priority_limit', orm['modules.StudentClassRegModuleInfo:priority_limit']),
            ('register_from_catalog', orm['modules.StudentClassRegModuleInfo:register_from_catalog']),
            ('visible_enrollments', orm['modules.StudentClassRegModuleInfo:visible_enrollments']),
            ('visible_meeting_times', orm['modules.StudentClassRegModuleInfo:visible_meeting_times']),
            ('show_unscheduled_classes', orm['modules.StudentClassRegModuleInfo:show_unscheduled_classes']),
            ('confirm_button_text', orm['modules.StudentClassRegModuleInfo:confirm_button_text']),
            ('view_button_text', orm['modules.StudentClassRegModuleInfo:view_button_text']),
            ('cancel_button_text', orm['modules.StudentClassRegModuleInfo:cancel_button_text']),
            ('temporarily_full_text', orm['modules.StudentClassRegModuleInfo:temporarily_full_text']),
            ('cancel_button_dereg', orm['modules.StudentClassRegModuleInfo:cancel_button_dereg']),
            ('progress_mode', orm['modules.StudentClassRegModuleInfo:progress_mode']),
            ('send_confirmation', orm['modules.StudentClassRegModuleInfo:send_confirmation']),
            ('show_emailcodes', orm['modules.StudentClassRegModuleInfo:show_emailcodes']),
        ))
        db.send_create_signal('modules', ['StudentClassRegModuleInfo'])
        
        # Adding model 'RemoteProfile'
        db.create_table('modules_remoteprofile', (
            ('id', orm['modules.RemoteProfile:id']),
            ('user', orm['modules.RemoteProfile:user']),
            ('program', orm['modules.RemoteProfile:program']),
            ('volunteer', orm['modules.RemoteProfile:volunteer']),
            ('need_bus', orm['modules.RemoteProfile:need_bus']),
        ))
        db.send_create_signal('modules', ['RemoteProfile'])
        
        # Adding model 'ClassRegModuleInfo'
        db.create_table('modules_classregmoduleinfo', (
            ('id', orm['modules.ClassRegModuleInfo:id']),
            ('module', orm['modules.ClassRegModuleInfo:module']),
            ('allow_coteach', orm['modules.ClassRegModuleInfo:allow_coteach']),
            ('set_prereqs', orm['modules.ClassRegModuleInfo:set_prereqs']),
            ('display_times', orm['modules.ClassRegModuleInfo:display_times']),
            ('times_selectmultiple', orm['modules.ClassRegModuleInfo:times_selectmultiple']),
            ('class_max_duration', orm['modules.ClassRegModuleInfo:class_max_duration']),
            ('class_max_size', orm['modules.ClassRegModuleInfo:class_max_size']),
            ('class_size_step', orm['modules.ClassRegModuleInfo:class_size_step']),
            ('director_email', orm['modules.ClassRegModuleInfo:director_email']),
            ('class_durations', orm['modules.ClassRegModuleInfo:class_durations']),
            ('teacher_class_noedit', orm['modules.ClassRegModuleInfo:teacher_class_noedit']),
            ('allowed_sections', orm['modules.ClassRegModuleInfo:allowed_sections']),
            ('session_counts', orm['modules.ClassRegModuleInfo:session_counts']),
            ('num_teacher_questions', orm['modules.ClassRegModuleInfo:num_teacher_questions']),
            ('num_class_choices', orm['modules.ClassRegModuleInfo:num_class_choices']),
            ('color_code', orm['modules.ClassRegModuleInfo:color_code']),
            ('allow_lateness', orm['modules.ClassRegModuleInfo:allow_lateness']),
            ('ask_for_room', orm['modules.ClassRegModuleInfo:ask_for_room']),
            ('progress_mode', orm['modules.ClassRegModuleInfo:progress_mode']),
        ))
        db.send_create_signal('modules', ['ClassRegModuleInfo'])
        
        # Adding model 'SATPrepTeacherModuleInfo'
        db.create_table('modules_satprepteachermoduleinfo', (
            ('id', orm['modules.SATPrepTeacherModuleInfo:id']),
            ('sat_math', orm['modules.SATPrepTeacherModuleInfo:sat_math']),
            ('sat_writ', orm['modules.SATPrepTeacherModuleInfo:sat_writ']),
            ('sat_verb', orm['modules.SATPrepTeacherModuleInfo:sat_verb']),
            ('mitid', orm['modules.SATPrepTeacherModuleInfo:mitid']),
            ('subject', orm['modules.SATPrepTeacherModuleInfo:subject']),
            ('user', orm['modules.SATPrepTeacherModuleInfo:user']),
            ('program', orm['modules.SATPrepTeacherModuleInfo:program']),
            ('section', orm['modules.SATPrepTeacherModuleInfo:section']),
        ))
        db.send_create_signal('modules', ['SATPrepTeacherModuleInfo'])
        
        # Adding model 'ProgramModuleObj'
        db.create_table('modules_programmoduleobj', (
            ('id', orm['modules.ProgramModuleObj:id']),
            ('program', orm['modules.ProgramModuleObj:program']),
            ('module', orm['modules.ProgramModuleObj:module']),
            ('seq', orm['modules.ProgramModuleObj:seq']),
            ('required', orm['modules.ProgramModuleObj:required']),
        ))
        db.send_create_signal('modules', ['ProgramModuleObj'])
        
        # Adding model 'CreditCardModuleInfo'
        db.create_table('modules_creditcardmoduleinfo', (
            ('id', orm['modules.CreditCardModuleInfo:id']),
            ('module', orm['modules.CreditCardModuleInfo:module']),
            ('base_cost', orm['modules.CreditCardModuleInfo:base_cost']),
        ))
        db.send_create_signal('modules', ['CreditCardModuleInfo'])
        
        # Adding model 'SATPrepAdminModuleInfo'
        db.create_table('modules_satprepadminmoduleinfo', (
            ('id', orm['modules.SATPrepAdminModuleInfo:id']),
            ('module', orm['modules.SATPrepAdminModuleInfo:module']),
            ('num_divisions', orm['modules.SATPrepAdminModuleInfo:num_divisions']),
        ))
        db.send_create_signal('modules', ['SATPrepAdminModuleInfo'])
        
        # Adding model 'DBReceipt'
        db.create_table('modules_dbreceipt', (
            ('id', orm['modules.DBReceipt:id']),
            ('action', orm['modules.DBReceipt:action']),
            ('program', orm['modules.DBReceipt:program']),
            ('receipt', orm['modules.DBReceipt:receipt']),
        ))
        db.send_create_signal('modules', ['DBReceipt'])
        
        # Adding ManyToManyField 'RemoteProfile.volunteer_times'
        db.create_table('modules_remoteprofile_volunteer_times', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('remoteprofile', models.ForeignKey(orm.RemoteProfile, null=False)),
            ('event', models.ForeignKey(orm['cal.Event'], null=False))
        ))
        
        # Adding ManyToManyField 'RemoteProfile.bus_runs'
        db.create_table('modules_remoteprofile_bus_runs', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('remoteprofile', models.ForeignKey(orm.RemoteProfile, null=False)),
            ('datatree', models.ForeignKey(orm['datatree.DataTree'], null=False))
        ))
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'StudentClassRegModuleInfo'
        db.delete_table('modules_studentclassregmoduleinfo')
        
        # Deleting model 'RemoteProfile'
        db.delete_table('modules_remoteprofile')
        
        # Deleting model 'ClassRegModuleInfo'
        db.delete_table('modules_classregmoduleinfo')
        
        # Deleting model 'SATPrepTeacherModuleInfo'
        db.delete_table('modules_satprepteachermoduleinfo')
        
        # Deleting model 'ProgramModuleObj'
        db.delete_table('modules_programmoduleobj')
        
        # Deleting model 'CreditCardModuleInfo'
        db.delete_table('modules_creditcardmoduleinfo')
        
        # Deleting model 'SATPrepAdminModuleInfo'
        db.delete_table('modules_satprepadminmoduleinfo')
        
        # Deleting model 'DBReceipt'
        db.delete_table('modules_dbreceipt')
        
        # Dropping ManyToManyField 'RemoteProfile.volunteer_times'
        db.delete_table('modules_remoteprofile_volunteer_times')
        
        # Dropping ManyToManyField 'RemoteProfile.bus_runs'
        db.delete_table('modules_remoteprofile_bus_runs')
        
    
    
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
            'anchor': ('AjaxForeignKey', ["orm['datatree.DataTree']"], {}),
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
            'parent': ('AjaxForeignKey', ["orm['datatree.DataTree']"], {'related_name': "'child_set'", 'null': 'True', 'blank': 'True'}),
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
            'user': ('AjaxForeignKey', ["orm['auth.User']"], {'null': 'True', 'blank': 'True'}),
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
            'user': ('AjaxForeignKey', ["orm['auth.User']"], {'null': 'True', 'blank': 'True'})
        },
        'modules.studentclassregmoduleinfo': {
            'cancel_button_dereg': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'cancel_button_text': ('django.db.models.fields.CharField', [], {'default': "'Cancel Registration'", 'max_length': '80'}),
            'class_cap_multiplier': ('django.db.models.fields.DecimalField', [], {'default': "'1.00'", 'max_digits': '3', 'decimal_places': '2'}),
            'class_cap_offset': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'confirm_button_text': ('django.db.models.fields.CharField', [], {'default': "'Confirm'", 'max_length': '80'}),
            'enforce_max': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['modules.ProgramModuleObj']"}),
            'priority_limit': ('django.db.models.fields.IntegerField', [], {'default': '3'}),
            'progress_mode': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'register_from_catalog': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'send_confirmation': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'show_emailcodes': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'show_unscheduled_classes': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'signup_verb': ('AjaxForeignKey', ["orm['datatree.DataTree']"], {'default': " lambda :GetNode(REG_VERB_BASE+'/Enrolled')"}),
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
            'anchor': ('AjaxForeignKey', ["orm['datatree.DataTree']"], {}),
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
