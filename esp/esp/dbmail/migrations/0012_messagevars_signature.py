# -*- coding: utf-8 -*-
# Migration to add HMAC signature field to MessageVars for secure deserialization

from django.db import migrations
import django.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('dbmail', '0011_populate_default_emaillists'),
    ]

    operations = [
        migrations.AddField(
            model_name='messagevars',
            name='signature',
            field=django.db.models.BinaryField(blank=True, null=True),
        ),
    ]
