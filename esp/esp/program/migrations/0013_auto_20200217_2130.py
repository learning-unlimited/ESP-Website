# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.core.validators

def set_my_defaults(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')
    for pm in ProgramModule.objects.all():
        mod = __import__("esp.program.modules.handlers.%s" % (pm.handler.lower()), (), (), [pm.handler])
        props = getattr(mod, pm.handler).module_properties()
        if type(props) is list:
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

def reverse_func(apps, schema_editor):
    pass  #

class Migration(migrations.Migration):

    dependencies = [
        ('program', '0012_remove_phasezerorecord_lottery_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='programmodule',
            name='choosable',
            field=models.IntegerField(null=False, default=0),
        ),
        migrations.RunPython(set_my_defaults, reverse_func),
        migrations.AlterField(
            model_name='programmodule',
            name='choosable',
            field=models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(2)]),
        ),
        migrations.AlterField(
            model_name='program',
            name='class_categories',
            field=models.ManyToManyField(help_text='You can add new categories or modify existing ones from <a href="/admin/program/classcategories/">the admin panel</a>.', to='program.ClassCategories', blank=True),
        ),
        migrations.AlterField(
            model_name='program',
            name='director_cc_email',
            field=models.EmailField(default=b'', help_text=b'If set, automated outgoing mail (except class cancellations) will be sent to this address <i>instead of</i> the director email. Use this if you do not want to spam the director email with teacher class registration emails. Otherwise, leave this field blank.', max_length=75, blank=True),
        ),
        migrations.AlterField(
            model_name='program',
            name='director_confidential_email',
            field=models.EmailField(default=b'', help_text=b'If set, confidential emails such as financial aid applications will be sent to this address <i>instead of</i> the director email.', max_length=75, blank=True),
        ),
        migrations.AlterField(
            model_name='volunteeroffer',
            name='shirt_type',
            field=models.CharField(blank=True, max_length=20, null=True, choices=[(b'M', b'Straight cut'), (b'F', b'Fitted cut')]),
        ),
    ]
