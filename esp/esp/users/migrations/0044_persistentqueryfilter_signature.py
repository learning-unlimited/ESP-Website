# -*- coding: utf-8 -*-
# Migration to add HMAC signature field to PersistentQueryFilter for secure deserialization

from django.db import migrations
import django.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0043_auto_20260327_1528'),
    ]

    operations = [
        migrations.AddField(
            model_name='persistentqueryfilter',
            name='signature',
            field=django.db.models.BinaryField(blank=True, null=True),
        ),
    ]
