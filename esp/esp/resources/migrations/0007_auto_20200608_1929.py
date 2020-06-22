# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resources', '0006_resourceassignment_returned'),
    ]

    operations = [
        migrations.CreateModel(
            name='AssignmentGroup',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.AddField(
            model_name='resourceassignment',
            name='assignment_group',
            field=models.ForeignKey(blank=True, to='resources.AssignmentGroup', null=True),
        ),
    ]
