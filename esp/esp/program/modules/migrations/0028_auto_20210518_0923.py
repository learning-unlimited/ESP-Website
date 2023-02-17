# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-05-18 09:23
from __future__ import unicode_literals

from __future__ import absolute_import
from __future__ import print_function
from django.db import migrations

def set_my_defaults(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    for pm in ProgramModule.objects.all():
        try:
            mod = __import__("esp.program.modules.handlers.%s" % (pm.handler.lower()), (), (), [pm.handler])
            props = getattr(mod, pm.handler).module_properties()
            if isinstance(props, list):
                if len(props) > 1:
                    props = [x for x in props if x['admin_title'] == pm.admin_title]
                    if len(props) != 1:
                        raise NameError('Found {} modules with name `{}`. Instead found {}'.format(len(props), pm.admin_title, ','.join([x['admin_title'] for x in getattr(mod, pm.handler).module_properties()])))
                    else:
                        props = props[0]
                else:
                    props = props[0] # IndexError here means there were no properties found, which is... bad
            pm.choosable = props['choosable']
            pm.save()
        except:
            print(("No handler for module %s" % (pm)))

def reverse_func(apps, schema_editor):
    pass  #

class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0027_auto_20210327_1019'),
    ]

    operations = [
        migrations.RunPython(set_my_defaults, reverse_func)
    ]
