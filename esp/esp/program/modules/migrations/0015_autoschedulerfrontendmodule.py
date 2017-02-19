# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0014_lotteryfrontendmodule'),
    ]

    operations = [
        migrations.CreateModel(
            name='AutoschedulerFrontendModule',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('modules.programmoduleobj',),
        ),
    ]
