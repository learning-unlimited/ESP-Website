# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('utils', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='printrequest',
            index=models.Index(fields=['time_executed'], name='utils_prq_exec_idx'),
        ),
        migrations.AddIndex(
            model_name='printrequest',
            index=models.Index(fields=['printer', 'time_executed'], name='utils_prq_prn_ex_idx'),
        ),
        migrations.AddIndex(
            model_name='printrequest',
            index=models.Index(fields=['time_requested'], name='utils_prq_req_idx'),
        ),
    ]
