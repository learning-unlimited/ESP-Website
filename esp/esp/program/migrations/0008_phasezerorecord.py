# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.utils.timezone
import esp.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_auto_20161011_1435'),
        ('program', '0007_auto_20160709_1856'),
    ]

    operations = [
        migrations.CreateModel(
            name='PhaseZeroRecord',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('phase_zero_time', models.DateTimeField(default=django.utils.timezone.now)),
                ('lottery_number', models.CharField(max_length=6)),
                ('program', models.ForeignKey(blank=True, to='program.Program', null=True)),
                ('user', esp.db.fields.AjaxForeignKey(to='users.ESPUser')),
            ],
        ),
    ]
