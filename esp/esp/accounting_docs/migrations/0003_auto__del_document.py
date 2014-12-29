# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting model 'Document'
        db.delete_table('accounting_docs_document')

        # Removing M2M table for field docs_next on 'Document'
        db.delete_table(db.shorten_name('accounting_docs_document_docs_next'))


    def backwards(self, orm):
        # Adding model 'Document'
        db.create_table('accounting_docs_document', (
            ('locator', self.gf('django.db.models.fields.CharField')(max_length=16, unique=True)),
            ('cc_ref', self.gf('django.db.models.fields.TextField')(default='', blank=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], null=True, blank=True)),
            ('txn', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['accounting_core.Transaction'])),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('anchor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['datatree.DataTree'])),
            ('doctype', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('accounting_docs', ['Document'])

        # Adding M2M table for field docs_next on 'Document'
        m2m_table_name = db.shorten_name('accounting_docs_document_docs_next')
        db.create_table(m2m_table_name, (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('from_document', models.ForeignKey(orm['accounting_docs.document'], null=False)),
            ('to_document', models.ForeignKey(orm['accounting_docs.document'], null=False))
        ))
        db.create_unique(m2m_table_name, ['from_document_id', 'to_document_id'])


    models = {
        
    }

    complete_apps = ['accounting_docs']