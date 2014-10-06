# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'LineItemType'
        db.create_table('accounting_lineitemtype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('amount_dec', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=9, decimal_places=2, blank=True)),
            ('program', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['program.Program'])),
            ('required', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('max_quantity', self.gf('django.db.models.fields.PositiveIntegerField')(default=1)),
            ('for_payments', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('for_finaid', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('accounting', ['LineItemType'])

        # Adding model 'FinancialAidGrant'
        db.create_table('accounting_financialaidgrant', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('request', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['program.FinancialAidRequest'])),
            ('amount_max_dec', self.gf('django.db.models.fields.DecimalField')(null=True, max_digits=9, decimal_places=2, blank=True)),
            ('percent', self.gf('django.db.models.fields.PositiveIntegerField')(null=True, blank=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('finalized', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('accounting', ['FinancialAidGrant'])

        # Adding model 'Account'
        db.create_table('accounting_account', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=200)),
            ('description', self.gf('django.db.models.fields.TextField')()),
            ('program', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['program.Program'], null=True, blank=True)),
            ('balance_dec', self.gf('django.db.models.fields.DecimalField')(default='0', max_digits=9, decimal_places=2)),
        ))
        db.send_create_signal('accounting', ['Account'])

        # Adding unique constraint on 'Account', fields ['name']
        db.create_unique('accounting_account', ['name'])

        # Adding model 'Transfer'
        db.create_table('accounting_transfer', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('source', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='transfer_source', null=True, to=orm['accounting.Account'])),
            ('destination', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='transfer_destination', null=True, to=orm['accounting.Account'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('line_item', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounting.LineItemType'], null=True, blank=True)),
            ('amount_dec', self.gf('django.db.models.fields.DecimalField')(max_digits=9, decimal_places=2)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('executed', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('accounting', ['Transfer'])


    def backwards(self, orm):
        # Removing unique constraint on 'Account', fields ['name']
        db.delete_unique('accounting_account', ['name'])

        # Deleting model 'LineItemType'
        db.delete_table('accounting_lineitemtype')

        # Deleting model 'FinancialAidGrant'
        db.delete_table('accounting_financialaidgrant')

        # Deleting model 'Account'
        db.delete_table('accounting_account')

        # Deleting model 'Transfer'
        db.delete_table('accounting_transfer')


    models = {
        'accounting.account': {
            'Meta': {'unique_together': "(('name',),)", 'object_name': 'Account'},
            'balance_dec': ('django.db.models.fields.DecimalField', [], {'default': "'0'", 'max_digits': '9', 'decimal_places': '2'}),
            'description': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '200'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']", 'null': 'True', 'blank': 'True'})
        },
        'accounting.financialaidgrant': {
            'Meta': {'object_name': 'FinancialAidGrant'},
            'amount_max_dec': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '9', 'decimal_places': '2', 'blank': 'True'}),
            'finalized': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'percent': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'request': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.FinancialAidRequest']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'accounting.lineitemtype': {
            'Meta': {'object_name': 'LineItemType'},
            'amount_dec': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '9', 'decimal_places': '2', 'blank': 'True'}),
            'for_finaid': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'for_payments': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'max_quantity': ('django.db.models.fields.PositiveIntegerField', [], {'default': '1'}),
            'program': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['program.Program']"}),
            'required': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        'accounting.transfer': {
            'Meta': {'object_name': 'Transfer'},
            'amount_dec': ('django.db.models.fields.DecimalField', [], {'max_digits': '9', 'decimal_places': '2'}),
            'destination': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'transfer_destination'", 'null': 'True', 'to': "orm['accounting.Account']"}),
            'executed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'line_item': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['accounting.LineItemType']", 'null': 'True', 'blank': 'True'}),
            'source': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'transfer_source'", 'null': 'True', 'to': "orm['accounting.Account']"}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
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
        'program.classcategories': {
            'Meta': {'object_name': 'ClassCategories'},
            'category': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'seq': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'symbol': ('django.db.models.fields.CharField', [], {'default': "'?'", 'max_length': '1'})
        },
        'program.financialaidrequest': {
            'Meta': {'object_name': 'FinancialAidRequest'},
            'approved': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
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
        }
    }

    complete_apps = ['accounting']