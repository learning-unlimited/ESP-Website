# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0016_merge'),
    ]

    operations = [
        migrations.CreateModel(
            name='CheckAvailabilityModule',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('modules.programmoduleobj',),
        ),
        migrations.CreateModel(
            name='FinAidApproveModule',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('modules.programmoduleobj',),
        ),
    ]
