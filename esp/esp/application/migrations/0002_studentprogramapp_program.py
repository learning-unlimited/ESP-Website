# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0001_initial'),
        ('application', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprogramapp',
            name='program',
            field=models.ForeignKey(to='program.Program'),
        ),
    ]
