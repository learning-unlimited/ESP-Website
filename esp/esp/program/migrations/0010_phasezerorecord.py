# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import esp.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0011_auto_20161017_1848'),
        ('program', '0006_classsubject_timestamp'),
    ]

    operations = [
        migrations.CreateModel(
            name='PhaseZeroRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('time', models.DateTimeField(auto_now_add=True)),
                ('lottery_number', models.IntegerField(null=True)),
                ('program', models.ForeignKey(to='program.Program', blank=True)),
                ('user', esp.db.fields.AjaxForeignKey(to='users.ESPUser')),
            ],
        ),
    ]
