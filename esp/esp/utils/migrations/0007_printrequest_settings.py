# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('utils', '0006_print_uploads_private_copies'),
    ]

    operations = [
        migrations.AddField(
            model_name='printrequest',
            name='settings_json',
            field=models.TextField(blank=True, default=''),
        ),
    ]
