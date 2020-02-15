# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import esp.program.modules.module_ext


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0001_initial'),
        ('modules', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentclassregmoduleinfo',
            name='signup_verb',
            field=models.ForeignKey(to='program.RegistrationType', help_text=b'Which verb to grant a student when they sign up for a class.', null=True),
        ),
        migrations.AddField(
            model_name='programmoduleobj',
            name='module',
            field=models.ForeignKey(to='program.ProgramModule'),
        ),
        migrations.AddField(
            model_name='programmoduleobj',
            name='program',
            field=models.ForeignKey(to='program.Program'),
        ),
        migrations.AddField(
            model_name='dbreceipt',
            name='program',
            field=models.ForeignKey(to='program.Program'),
        ),
        migrations.AddField(
            model_name='classregmoduleinfo',
            name='module',
            field=models.ForeignKey(to='modules.ProgramModuleObj'),
        ),
    ]
