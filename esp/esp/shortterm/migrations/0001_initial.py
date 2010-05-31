# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'AdLogEntry'
        db.create_table('shortterm_adlogentry', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('ts', self.gf('django.db.models.fields.DateTimeField')()),
            ('ipaddr', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('agent', self.gf('django.db.models.fields.CharField')(max_length=256)),
        ))
        db.send_create_signal('shortterm', ['AdLogEntry'])

        # Adding model 'VolunteerRegistration'
        db.create_table('shortterm_volunteerregistration', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('your_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('email_address', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('phone_number', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('availability', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('notes', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
        ))
        db.send_create_signal('shortterm', ['VolunteerRegistration'])

        # Adding model 'ResponseForm'
        db.create_table('shortterm_responseform', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('contact_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('position', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('school', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('mailing_address', self.gf('django.db.models.fields.TextField')()),
            ('xeroxable_flier_for_summer_hssp', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('xeroxable_flier_for_junction', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('catalog_of_all_2007_to_2008_esp_courses', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('xeroxable_fliers_for_all_2008_to_2009_esp_courses', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('splash_on_wheels_application', self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True, blank=True)),
            ('bulk_financial_aid_application', self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True, blank=True)),
        ))
        db.send_create_signal('shortterm', ['ResponseForm'])


    def backwards(self, orm):
        
        # Deleting model 'AdLogEntry'
        db.delete_table('shortterm_adlogentry')

        # Deleting model 'VolunteerRegistration'
        db.delete_table('shortterm_volunteerregistration')

        # Deleting model 'ResponseForm'
        db.delete_table('shortterm_responseform')


    models = {
        'shortterm.adlogentry': {
            'Meta': {'object_name': 'AdLogEntry'},
            'agent': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipaddr': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'ts': ('django.db.models.fields.DateTimeField', [], {})
        },
        'shortterm.responseform': {
            'Meta': {'object_name': 'ResponseForm'},
            'bulk_financial_aid_application': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'catalog_of_all_2007_to_2008_esp_courses': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'contact_name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mailing_address': ('django.db.models.fields.TextField', [], {}),
            'position': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'school': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'splash_on_wheels_application': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'xeroxable_flier_for_junction': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'xeroxable_flier_for_summer_hssp': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'xeroxable_fliers_for_all_2008_to_2009_esp_courses': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'})
        },
        'shortterm.volunteerregistration': {
            'Meta': {'object_name': 'VolunteerRegistration'},
            'availability': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email_address': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'notes': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'phone_number': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            'your_name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['shortterm']
