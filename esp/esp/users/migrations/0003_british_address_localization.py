# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_zipcode_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='contactinfo',
            name='address_locality',
            field=models.CharField(default=b'', max_length=255, verbose_name=b'Locality', blank=True),
        ),
        migrations.AlterField(
            model_name='contactinfo',
            name='address_city',
            field=models.CharField(max_length=50, null=True, verbose_name=b'Town', blank=True),
        ),
        migrations.AlterField(
            model_name='contactinfo',
            name='address_state',
            field=models.CharField(max_length=255, null=True, verbose_name=b'County', blank=True),
        ),
        migrations.AlterField(
            model_name='contactinfo',
            name='address_street',
            field=models.CharField(max_length=100, null=True, verbose_name=b'Number and Street', blank=True),
        ),
        migrations.AlterField(
            model_name='contactinfo',
            name='address_zip',
            field=models.CharField(max_length=15, null=True, verbose_name=b'Postal code', blank=True),
        ),
    ]
