# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'LineItemType'
        db.delete_table('accounting_core_lineitemtype')

        # Deleting model 'Balance'
        db.delete_table('accounting_core_balance')

        # Deleting model 'LineItem'
        db.delete_table('accounting_core_lineitem')

        # Deleting model 'Transaction'
        db.delete_table('accounting_core_transaction')


    def backwards(self, orm):
        # Adding model 'LineItemType'
        db.create_table('accounting_core_lineitemtype', (
            ('finaid_amount', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=9, decimal_places=2)),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('anchor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='accounting_lineitemtype', null=True, to=orm['datatree.DataTree'])),
            ('amount', self.gf('django.db.models.fields.DecimalField')(default='0.0', max_digits=9, decimal_places=2)),
            ('finaid_anchor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='accounting_finaiditemtype', null=True, to=orm['datatree.DataTree'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('accounting_core', ['LineItemType'])

        # Adding model 'Balance'
        db.create_table('accounting_core_balance', (
            ('_order', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('past', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounting_core.Balance'], null=True)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=16, decimal_places=2)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='balance', to=orm['auth.User'])),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')()),
            ('anchor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='balance', to=orm['datatree.DataTree'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('accounting_core', ['Balance'])

        # Adding model 'LineItem'
        db.create_table('accounting_core_lineitem', (
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=9, decimal_places=2)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(related_name='accounting_lineitem', to=orm['auth.User'])),
            ('li_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounting_core.LineItemType'])),
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('transaction', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounting_core.Transaction'])),
            ('anchor', self.gf('django.db.models.fields.related.ForeignKey')(related_name='accounting_lineitem', to=orm['datatree.DataTree'])),
            ('posted_to', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounting_core.Balance'], null=True, blank=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('accounting_core', ['LineItem'])

        # Adding model 'Transaction'
        db.create_table('accounting_core_transaction', (
            ('text', self.gf('django.db.models.fields.TextField')()),
            ('complete', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')()),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('accounting_core', ['Transaction'])


    models = {
        
    }

    complete_apps = ['accounting_core']