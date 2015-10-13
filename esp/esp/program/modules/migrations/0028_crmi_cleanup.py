# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'StudentClassRegModuleInfo.show_unscheduled_classes'
        db.delete_column('modules_studentclassregmoduleinfo', 'show_unscheduled_classes')

        # Deleting field 'ClassRegModuleInfo.display_times'
        db.delete_column('modules_classregmoduleinfo', 'display_times')

        # Deleting field 'ClassRegModuleInfo.class_durations'
        db.delete_column('modules_classregmoduleinfo', 'class_durations')

        # Deleting field 'ClassRegModuleInfo.director_email'
        db.delete_column('modules_classregmoduleinfo', 'director_email')

        # Deleting field 'ClassRegModuleInfo.teacher_class_noedit'
        db.delete_column('modules_classregmoduleinfo', 'teacher_class_noedit')

        # Deleting field 'ClassRegModuleInfo.times_selectmultiple'
        db.delete_column('modules_classregmoduleinfo', 'times_selectmultiple')

        # Deleting field 'ClassRegModuleInfo.num_class_choices'
        db.delete_column('modules_classregmoduleinfo', 'num_class_choices')


    def backwards(self, orm):
        # Adding field 'StudentClassRegModuleInfo.show_unscheduled_classes'
        db.add_column('modules_studentclassregmoduleinfo', 'show_unscheduled_classes',
                      self.gf('django.db.models.fields.BooleanField')(default=True),
                      keep_default=False)

        # Adding field 'ClassRegModuleInfo.display_times'
        db.add_column('modules_classregmoduleinfo', 'display_times',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'ClassRegModuleInfo.class_durations'
        db.add_column('modules_classregmoduleinfo', 'class_durations',
                      self.gf('django.db.models.fields.CharField')(max_length=128, null=True, blank=True),
                      keep_default=False)

        # Adding field 'ClassRegModuleInfo.director_email'
        db.add_column('modules_classregmoduleinfo', 'director_email',
                      self.gf('django.db.models.fields.EmailField')(max_length=75, null=True, blank=True),
                      keep_default=False)

        # Adding field 'ClassRegModuleInfo.teacher_class_noedit'
        db.add_column('modules_classregmoduleinfo', 'teacher_class_noedit',
                      self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True),
                      keep_default=False)

        # Adding field 'ClassRegModuleInfo.times_selectmultiple'
        db.add_column('modules_classregmoduleinfo', 'times_selectmultiple',
                      self.gf('django.db.models.fields.BooleanField')(default=False),
                      keep_default=False)

        # Adding field 'ClassRegModuleInfo.num_class_choices'
        db.add_column('modules_classregmoduleinfo', 'num_class_choices',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=1, null=True, blank=True),
                      keep_default=False)


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
        'modules.creditcardsettings': {
            'Meta': {'object_name': 'CreditCardSettings'},
            'host_payment_form': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'invoice_prefix': ('django.db.models.fields.CharField', [], {'default': "'mit'", 'max_length': '80'}),
            'module': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['modules.ProgramModuleObj']"}),
            'offer_donation': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'post_url': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '255'}),
            'store_id': ('django.db.models.fields.CharField', [], {'default': "''", 'max_length': '80'})
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
        'modules.remoteprofile': {
            'Meta': {'object_name': 'RemoteProfile'},
            'bus_runs': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'bus_teachers'", 'blank': 'True', 'to': "orm['datatree.DataTree']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'need_bus': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']", 'null': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'}),
            'volunteer': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'volunteer_times': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "'teacher_volunteer_set'", 'blank': 'True', 'to': "orm['cal.Event']"})
        },
        'modules.satprepteachermoduleinfo': {
            'Meta': {'unique_together': "(('user', 'program'),)", 'object_name': 'SATPrepTeacherModuleInfo'},
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
        'program.classcategories': {
            'Meta': {'object_name': 'ClassCategories'},
            'category': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'seq': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'symbol': ('django.db.models.fields.CharField', [], {'default': "'?'", 'max_length': '1'})
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
        'program.registrationtype': {
            'Meta': {'unique_together': "(('name', 'category'),)", 'object_name': 'RegistrationType'},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'description': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'displayName': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '32'})
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
        }
    }

    complete_apps = ['modules']
