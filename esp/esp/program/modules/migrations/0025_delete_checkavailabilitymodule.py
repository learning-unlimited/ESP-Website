# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0024_merge'),
    ]

    operations = [
        migrations.DeleteModel(
            name='CheckAvailabilityModule',
        ),
    ]
