# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0032_add_lottery_run_persistence_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='NametagBack',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('source', models.TextField()),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='nametag_backs', to='program.Program')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='nametagback',
            unique_together=set([('program', 'name')]),
        ),
    ]
