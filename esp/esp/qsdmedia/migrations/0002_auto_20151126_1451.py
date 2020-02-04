# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('qsdmedia', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='paper',
            name='media',
        ),
        migrations.RemoveField(
            model_name='paper',
            name='type',
        ),
        migrations.RemoveField(
            model_name='picture',
            name='media',
        ),
        migrations.RemoveField(
            model_name='video',
            name='media',
        ),
        migrations.DeleteModel(
            name='Paper',
        ),
        migrations.DeleteModel(
            name='PaperType',
        ),
        migrations.DeleteModel(
            name='Picture',
        ),
        migrations.DeleteModel(
            name='Video',
        ),
    ]
