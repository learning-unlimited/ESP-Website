# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0002_resource_user'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='resourcetype',
            name='distancefunc',
        ),
    ]
