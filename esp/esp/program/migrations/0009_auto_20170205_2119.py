# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0008_classsubject_class_style'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='registrationprofile',
            name='email_verified',
        ),
        migrations.RemoveField(
            model_name='registrationprofile',
            name='emailverifycode',
        ),
    ]
