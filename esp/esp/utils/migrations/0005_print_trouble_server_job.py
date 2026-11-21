# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('utils', '0004_printer_archived'),
    ]

    operations = [
        migrations.AddField(
            model_name='printer',
            name='trouble',
            field=models.TextField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='printer',
            name='trouble_since',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='printrequest',
            name='server_job',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]
