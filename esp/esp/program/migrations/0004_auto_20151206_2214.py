# -*- coding: utf-8 -*-
# This is a temporary migration and can be deleted once it's been faked
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0003_auto_20151108_1612'),
    ]

    operations = [
        migrations.AlterField(
            model_name='archiveclass',
            name='year',
            field=models.IntegerField(),
        ),
    ]
