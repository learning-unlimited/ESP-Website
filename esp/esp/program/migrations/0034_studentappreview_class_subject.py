# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0033_cleanup_duplicate_registration_profiles'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentappreview',
            name='class_subject',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='program.ClassSubject'),
        ),
    ]
