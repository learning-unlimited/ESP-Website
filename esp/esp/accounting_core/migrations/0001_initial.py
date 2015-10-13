# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'LineItemType'
        db.create_table('accounting_core_lineitemtype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('amount', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=9, decimal_places=2)),
            ('anchor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='accounting_lineitemtype', null=True, to=orm['datatree.DataTree'])),
            ('finaid_amount', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=9, decimal_places=2)),
            ('finaid_anchor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='accounting_finaiditemtype', null=True, to=orm['datatree.DataTree'])),
        ))
        db.send_create_signal('accounting_core', ['LineItemType'])

        # Adding model 'Balance'
        db.create_table('accounting_core_balance', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('anchor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='balance', to=orm['datatree.DataTree'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='balance', to=orm['auth.User'])),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')()),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=16, decimal_places=2)),
            ('past', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounting_core.Balance'], null=True)),
            ('_order', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('accounting_core', ['Balance'])

        # Adding model 'Transaction'
        db.create_table('accounting_core_transaction', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')()),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('complete', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('accounting_core', ['Transaction'])

        # Adding model 'LineItem'
        db.create_table('accounting_core_lineitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('transaction', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounting_core.Transaction'])),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='accounting_lineitem', to=orm['auth.User'])),
            ('anchor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='accounting_lineitem', to=orm['datatree.DataTree'])),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=9, decimal_places=2)),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('li_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounting_core.LineItemType'])),
            ('posted_to', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounting_core.Balance'], null=True, blank=True)),
        ))
        db.send_create_signal('accounting_core', ['LineItem'])


    def backwards(self, orm):
        # Deleting model 'LineItemType'
        db.delete_table('accounting_core_lineitemtype')

        # Deleting model 'Balance'
        db.delete_table('accounting_core_balance')

        # Deleting model 'Transaction'
        db.delete_table('accounting_core_transaction')

        # Deleting model 'LineItem'
        db.delete_table('accounting_core_lineitem')


    models = {
        'accounting_core.balance': {
            'Meta': {'ordering': "('_order',)", 'object_name': 'Balance'},
            '_order': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '16', 'decimal_places': '2'}),
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'balance'", 'to': "orm['datatree.DataTree']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'past': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['accounting_core.Balance']", 'null': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'balance'", 'to': "orm['auth.User']"})
        },
        'accounting_core.lineitem': {
            'Meta': {'object_name': 'LineItem'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '9', 'decimal_places': '2'}),
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'accounting_lineitem'", 'to': "orm['datatree.DataTree']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'li_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['accounting_core.LineItemType']"}),
            'posted_to': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['accounting_core.Balance']", 'null': 'True', 'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'transaction': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['accounting_core.Transaction']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'accounting_lineitem'", 'to': "orm['auth.User']"})
        },
        'accounting_core.lineitemtype': {
            'Meta': {'object_name': 'LineItemType'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '9', 'decimal_places': '2'}),
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'accounting_lineitemtype'", 'null': 'True', 'to': "orm['datatree.DataTree']"}),
            'finaid_amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.0'", 'max_digits': '9', 'decimal_places': '2'}),
            'finaid_anchor': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'accounting_finaiditemtype'", 'null': 'True', 'to': "orm['datatree.DataTree']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {})
        },
        'accounting_core.transaction': {
            'Meta': {'object_name': 'Transaction'},
            'complete': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {})
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
        }
    }

    complete_apps = ['accounting_core']