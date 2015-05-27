# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    depends_on = (
        ("program", "0046_delete_anchors"),
    )

    def forwards(self, orm):
        # Removing unique constraint on 'DataTree', fields ['name', 'parent']
        try:
            db.delete_unique('datatree_datatree', ['name', 'parent_id'])
        except ValueError:
            # Not sure why South thinks the unique constraint existed but my database
            # doesn't; ignore the error
            pass

        # Deleting model 'DataTree'
        db.delete_table('datatree_datatree')


    def backwards(self, orm):
        # Adding model 'DataTree'
        db.create_table('datatree_datatree', (
            ('parent', self.gf('django.db.models.fields.related.ForeignKey')(related_name='child_set', null=True, to=orm['datatree.DataTree'], blank=True)),
            ('rangestart', self.gf('django.db.models.fields.IntegerField')()),
            ('range_correct', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('uri_correct', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('rangeend', self.gf('django.db.models.fields.IntegerField')()),
            ('friendly_name', self.gf('django.db.models.fields.TextField')()),
            ('uri', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('lock_table', self.gf('django.db.models.fields.IntegerField')(default=0)),
        ))
        db.send_create_signal('datatree', ['DataTree'])

        # Adding unique constraint on 'DataTree', fields ['name', 'parent']
        db.create_unique('datatree_datatree', ['name', 'parent_id'])


    models = {
        
    }

    complete_apps = ['datatree']
