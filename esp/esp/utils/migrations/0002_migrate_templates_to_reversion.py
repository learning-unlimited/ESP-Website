# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
import reversion

import esp.utils.admin # required to register the model with reversion

def string(obj):
    return "<Override: id=%s, name=%s, version=%s>" % (obj.id, obj.name, obj.version, )

class Migration(DataMigration):
    
    depends_on = (
        ("reversion", "0005_auto__add_field_revision_manager_slug"),
    )

    def forwards(self, orm):
        "Write your forwards methods here."
        reversion.register(orm.TemplateOverride)
        templateoverrides = orm.TemplateOverride.objects.all().order_by('id')
        pages = {}
        for override in templateoverrides:
            with reversion.create_revision():
                reversion.set_comment("Migrating old versions")
                name = override.name
                if name not in pages:
                    pages[name] = orm.TemplateOverride()
                pages[name].name = override.name
                pages[name].content = override.content
                pages[name].version = override.version
                override.delete()
                pages[name].save()

    def backwards(self, orm):
        "Write your backwards methods here."
        raise RuntimeError("Cannot reverse this migration.")


    models = {
        'utils.templateoverride': {
            'Meta': {'unique_together': "(('name', 'version'),)", 'object_name': 'TemplateOverride'},
            'content': ('django.db.models.fields.TextField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'version': ('django.db.models.fields.IntegerField', [], {})
        }
    }

    complete_apps = ['utils']
