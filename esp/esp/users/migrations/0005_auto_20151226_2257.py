# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_auto_20151205_0248'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='teacherinfo',
            name='full_legal_name',
        ),
        migrations.RemoveField(
            model_name='teacherinfo',
            name='mail_reimbursement',
        ),
        migrations.RemoveField(
            model_name='teacherinfo',
            name='student_id',
        ),
        migrations.RemoveField(
            model_name='teacherinfo',
            name='university_email',
        ),
    ]
