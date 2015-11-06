# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0001_initial'),
        ('cal', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='program',
            field=models.ForeignKey(blank=True, to='program.Program', null=True),
        ),
    ]
