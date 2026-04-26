# -*- coding: utf-8 -*-

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0003_auto_20151108_1612'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='programcheckitem',
            name='program',
        ),
        migrations.RemoveField(
            model_name='classsection',
            name='checklist_progress',
        ),
        migrations.RemoveField(
            model_name='classsubject',
            name='checklist_progress',
        ),
        migrations.DeleteModel(
            name='ProgramCheckItem',
        ),
    ]
