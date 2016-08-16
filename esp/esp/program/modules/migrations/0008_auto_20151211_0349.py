# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0007_auto_20151211_0329'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='classregmoduleinfo',
            name='module',
        ),
        migrations.RemoveField(
            model_name='studentclassregmoduleinfo',
            name='module',
        ),
    ]
