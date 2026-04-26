# -*- coding: utf-8 -*-

from django.db import migrations


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
