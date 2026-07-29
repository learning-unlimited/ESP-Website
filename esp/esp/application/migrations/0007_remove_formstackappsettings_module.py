# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0006_auto_20151211_0329'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='formstackappsettings',
            name='module',
        ),
    ]
