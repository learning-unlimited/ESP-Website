# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0006_classsubject_timestamp'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='classimplication',
            name='cls',
        ),
        migrations.RemoveField(
            model_name='classimplication',
            name='parent',
        ),
        migrations.DeleteModel(
            name='ClassImplication',
        ),
    ]
