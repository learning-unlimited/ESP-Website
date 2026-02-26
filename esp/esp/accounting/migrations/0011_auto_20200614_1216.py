# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0010_lineitemoptions_is_custom'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lineitemoptions',
            name='is_custom',
            field=models.BooleanField(default=False, help_text='Should the student be allowed to specify a custom amount for this option?'),
        ),
    ]
