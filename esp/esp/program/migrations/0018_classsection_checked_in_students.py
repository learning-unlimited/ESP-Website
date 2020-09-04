# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0017_regtype_defaults'),
    ]

    operations = [
        migrations.AddField(
            model_name='classsection',
            name='checked_in_students',
            field=models.IntegerField(default=0),
        ),
    ]
