# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0010_merge'),
    ]

    operations = [
        migrations.RenameField(
            model_name='ajaxchangelogentry',
            old_name='isScheduling',
            new_name='is_scheduling',
        ),
    ]
