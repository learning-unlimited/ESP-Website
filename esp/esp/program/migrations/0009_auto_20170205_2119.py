# -*- coding: utf-8 -*-

from django.db import migrations


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
