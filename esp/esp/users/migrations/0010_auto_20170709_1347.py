# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0008_auto_20170131_0056'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='zipcodesearches',
            options={'verbose_name_plural': 'Zip Code Searches'},
        ),
    ]
