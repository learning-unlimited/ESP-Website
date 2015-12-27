# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0005_auto_20151127_2258'),
    ]

    operations = [
        migrations.AddField(
            model_name='transfer',
            name='paid_in',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, blank=True, to='accounting.Transfer', help_text=b'If this transfer is for a fee that has been paid, references the transfer for the payment transaction.', null=True),
        ),
    ]
