# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'SATPrepTeacherModuleInfo', fields ['user', 'program']
        try:
            db.delete_unique('modules_satprepteachermoduleinfo', ['user_id', 'program_id'])
        # Apparently this unique constraint doesn't always exist
        except ValueError:
            pass

        # Deleting model 'RemoteProfile'
        db.delete_table('modules_remoteprofile')

        # Removing M2M table for field volunteer_times on 'RemoteProfile'
        db.delete_table(db.shorten_name('modules_remoteprofile_volunteer_times'))

        # Removing M2M table for field bus_runs on 'RemoteProfile'
        db.delete_table(db.shorten_name('modules_remoteprofile_bus_runs'))

        # Deleting model 'SATPrepTeacherModuleInfo'
        db.delete_table('modules_satprepteachermoduleinfo')

        # Deleting model 'CreditCardSettings'
        db.delete_table('modules_creditcardsettings')


    def backwards(self, orm):
        # Adding model 'RemoteProfile'
        db.create_table('modules_remoteprofile', (
            ('program', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['program.Program'], null=True, blank=True)),
            ('volunteer', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('need_bus', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('modules', ['RemoteProfile'])

        # Adding M2M table for field volunteer_times on 'RemoteProfile'
        m2m_table_name = db.shorten_name('modules_remoteprofile_volunteer_times')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('remoteprofile', models.ForeignKey(orm['modules.remoteprofile'], null=False)),
            ('event', models.ForeignKey(orm['cal.event'], null=False))
        ))
        db.create_unique(m2m_table_name, ['remoteprofile_id', 'event_id'])

        # Adding M2M table for field bus_runs on 'RemoteProfile'
        m2m_table_name = db.shorten_name('modules_remoteprofile_bus_runs')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('remoteprofile', models.ForeignKey(orm['modules.remoteprofile'], null=False)),
            ('datatree', models.ForeignKey(orm['datatree.datatree'], null=False))
        ))
        db.create_unique(m2m_table_name, ['remoteprofile_id', 'datatree_id'])

        # Adding model 'SATPrepTeacherModuleInfo'
        db.create_table('modules_satprepteachermoduleinfo', (
            ('program', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['program.Program'], null=True, blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('sat_math', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('mitid', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('section', self.gf('django.db.models.fields.CharField')(max_length=5)),
            ('sat_writ', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('sat_verb', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subject', self.gf('django.db.models.fields.CharField')(max_length=32)),
        ))
        db.send_create_signal('modules', ['SATPrepTeacherModuleInfo'])

        # Adding unique constraint on 'SATPrepTeacherModuleInfo', fields ['user', 'program']
        db.create_unique('modules_satprepteachermoduleinfo', ['user_id', 'program_id'])

        # Adding model 'CreditCardSettings'
        db.create_table('modules_creditcardsettings', (
            ('post_url', self.gf('django.db.models.fields.CharField')(default='', max_length=255)),
            ('module', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['modules.ProgramModuleObj'])),
            ('host_payment_form', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('offer_donation', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('invoice_prefix', self.gf('django.db.models.fields.CharField')(default='mit', max_length=80)),
            ('store_id', self.gf('django.db.models.fields.CharField')(default='', max_length=80)),
        ))
        db.send_create_signal('modules', ['CreditCardSettings'])


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
