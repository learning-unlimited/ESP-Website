# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'ResponseForm'
        db.delete_table('shortterm_responseform')

        # Deleting model 'VolunteerRegistration'
        db.delete_table('shortterm_volunteerregistration')

        # Deleting model 'AdLogEntry'
        db.delete_table('shortterm_adlogentry')


    def backwards(self, orm):
        # Adding model 'ResponseForm'
        db.create_table('shortterm_responseform', (
            ('catalog_of_all_2007_to_2008_esp_courses', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('xeroxable_flier_for_summer_hssp', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('mailing_address', self.gf('django.db.models.fields.TextField')()),
            ('contact_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('splash_on_wheels_application', self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True, blank=True)),
            ('school', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('xeroxable_fliers_for_all_2008_to_2009_esp_courses', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('bulk_financial_aid_application', self.gf('django.db.models.fields.files.FileField')(max_length=100, null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('xeroxable_flier_for_junction', self.gf('django.db.models.fields.BooleanField')(default=False, blank=True)),
            ('position', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
        ))
        db.send_create_signal('shortterm', ['ResponseForm'])

        # Adding model 'VolunteerRegistration'
        db.create_table('shortterm_volunteerregistration', (
            ('phone_number', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('notes', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('your_name', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('email_address', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('availability', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('shortterm', ['VolunteerRegistration'])

        # Adding model 'AdLogEntry'
        db.create_table('shortterm_adlogentry', (
            ('ipaddr', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('agent', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('ts', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('shortterm', ['AdLogEntry'])


    models = {}

    complete_apps = ['shortterm']
