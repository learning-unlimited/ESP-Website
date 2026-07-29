# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0003_remove_transfer_executed'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='balance_dec',
        ),
    ]
