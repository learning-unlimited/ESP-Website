# encoding: utf-8
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

from esp.utils.models import TemplateOverride
import string

class Migration(DataMigration):

    def forwards(self, orm):
        "Write your forwards methods here."
        space = ['','']
        overrides = {}
        for i in range(0,4):
            space[0] = '' +  ' '*(i&(1<<0))
            space[1] = '' + ' '*((i&(1<<1))>>1)
            contains_txt = "{%" + space[0] + "navbar_gen" + space[1] + "%}"
            override = [x for x in TemplateOverride.objects.filter(content__contains=contains_txt)]
            for o in override:
                if o.name in overrides.keys():
                    if overrides[o.name].version < o.version:
                        overrides[o.name] = o
                else:
                    overrides[o.name] = o
        for o in overrides.keys():
            override = [x for x in TemplateOverride.objects.filter(name=o)]
            max_vers = 0
            for i in range(0, len(override)):
                if override[i].version > max_vers:
                    max_vers = override[i].version
            if overrides[o].version < max_vers:
                continue
            overrides[o].content = string.replace(overrides[o].content, contains_txt, string.replace(contains_txt, "navbar_gen", "navbar_gen request.path request.user navbar_list"))
            overrides[o].save()
        
    

    def backwards(self, orm):
        "Write your backwards methods here."
        space = ['','']
        overrides = {}
        for i in range(0,4):
            space[0] = '' +  ' '*(i&(1<<0))
            space[1] = '' + ' '*((i&(1<<1))>>1)
            contains_txt = "{%" + space[0] + "navbar_gen request.path request.user navbar_list" + space[1] + "%}"
            override = [x for x in TemplateOverride.objects.filter(content__contains=contains_txt)]
            for o in override:
                if o.name in overrides.keys():
                    if overrides[o.name].version < o.version:
                        overrides[o.name] = o
                else:
                    overrides[o.name] = o
        for o in overrides.keys():
            override = [x for x in TemplateOverride.objects.filter(name=o)]
            max_vers = 0
            for i in range(0, len(override)):
                if override[i].version > max_vers:
                    max_vers = override[i].version
            if overrides[o].version < max_vers:
                continue
            overrides[o].content = string.replace(overrides[o].content, contains_txt, string.replace(contains_txt, "navbar_gen request.path request.user navbar_list", "navbar_gen"))
            overrides[o].save()


    models = {
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
        'web.navbarcategory': {
            'Meta': {'object_name': 'NavBarCategory'},
            'anchor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['datatree.DataTree']", 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'include_auto_links': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'long_explanation': ('django.db.models.fields.TextField', [], {}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'web.navbarentry': {
            'Meta': {'object_name': 'NavBarEntry'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['web.NavBarCategory']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'indent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'link': ('django.db.models.fields.CharField', [], {'max_length': '256', 'null': 'True', 'blank': 'True'}),
            'path': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'navbar'", 'null': 'True', 'to': "orm['datatree.DataTree']"}),
            'sort_rank': ('django.db.models.fields.IntegerField', [], {}),
            'text': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        }
    }

    complete_apps = ['web']
