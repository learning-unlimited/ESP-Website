# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models
import esp.program.modules.base


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0018_studentonsite'),
    ]

    operations = [
        migrations.AlterField(
            model_name='programmoduleobj',
            name='required_label',
            field=models.CharField(default='', max_length=80, blank=True),
        ),
    ]
