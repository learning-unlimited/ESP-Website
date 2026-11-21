# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import esp.utils.models


class Migration(migrations.Migration):

    dependencies = [
        ('utils', '0005_print_trouble_server_job'),
    ]

    operations = [
        migrations.AlterField(
            model_name='printrequest',
            name='file',
            field=models.FileField(blank=True, null=True, storage=esp.utils.models.PrintUploadStorage(), upload_to='%Y/%m/'),
        ),
        migrations.AddField(
            model_name='printrequest',
            name='copies',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
