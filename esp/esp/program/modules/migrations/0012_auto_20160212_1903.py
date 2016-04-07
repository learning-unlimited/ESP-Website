# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0011_auto_20160212_1853'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ajaxchangelogentry',
            name='comment',
            field=models.CharField(default='', max_length=256),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='ajaxchangelogentry',
            name='locked',
            field=models.NullBooleanField(),
        ),
    ]
