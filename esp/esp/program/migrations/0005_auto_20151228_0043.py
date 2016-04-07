# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0004_auto_20151126_2220'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='program',
            options={'ordering': ('-id',)},
        ),
    ]
