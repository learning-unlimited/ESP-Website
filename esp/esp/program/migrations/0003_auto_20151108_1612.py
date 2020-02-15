# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0002_auto_20151004_1715'),
    ]

    operations = [
        migrations.AlterField(
            model_name='program',
            name='program_size_max',
            field=models.IntegerField(help_text=b'Set to 0 for no cap. Student registration performance is best when no cap is set.', null=True),
        ),
    ]
