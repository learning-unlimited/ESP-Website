# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2021-05-26 19:21
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0012_auto_20200812_1128'),
    ]

    operations = [
        migrations.AlterField(
            model_name='financialaidgrant',
            name='amount_max_dec',
            field=models.DecimalField(blank=True, decimal_places=2, help_text=b'Enter a number here to grant a dollar value of financial aid.  The grant will cover this amount or the full cost, whichever is less.', max_digits=9, null=True),
        ),
        migrations.AlterField(
            model_name='financialaidgrant',
            name='percent',
            field=models.PositiveIntegerField(blank=True, help_text=b'Enter an integer between 0 and 100 here to grant a certain percentage discount after the above dollar credit is applied.  0 means no additional discount, 100 means no payment required.', null=True),
        ),
    ]
