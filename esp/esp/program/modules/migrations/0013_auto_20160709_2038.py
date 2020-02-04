# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0012_auto_20160212_1903'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnenrollModule',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('modules.programmoduleobj',),
        ),
        migrations.RemoveField(
            model_name='studentclassregmoduleinfo',
            name='signup_verb',
        ),
    ]
