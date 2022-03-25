# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
import esp.program.modules.base


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0020_auto_20200503_1046'),
    ]

    operations = [
        migrations.CreateModel(
            name='OnSiteAttendance',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('modules.programmoduleobj',),
        ),
        migrations.CreateModel(
            name='OnSiteCheckoutModule',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('modules.programmoduleobj',),
        ),
        migrations.CreateModel(
            name='StudentAcknowledgementModule',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('modules.programmoduleobj',),
        ),
        migrations.CreateModel(
            name='TeacherOnsite',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('modules.programmoduleobj', esp.program.modules.base.CoreModule),
        ),
    ]
