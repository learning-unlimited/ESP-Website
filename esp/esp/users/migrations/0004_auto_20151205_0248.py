# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_auto_20151109_0048'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='espuser_profile',
            name='user',
        ),
        migrations.DeleteModel(
            name='ESPUser_Profile',
        ),
    ]
