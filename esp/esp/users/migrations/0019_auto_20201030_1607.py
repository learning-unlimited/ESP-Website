# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0018_auto_20200531_1357'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactinfo',
            name='address_state',
            field=models.CharField(max_length=32, null=True, verbose_name=b'State', blank=True),
        ),
    ]
