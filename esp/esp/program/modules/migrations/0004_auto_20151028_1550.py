# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import esp.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0002_auto_20151004_1715'),
        ('modules', '0003_auto_20151004_1715'),
    ]

    operations = [
        migrations.CreateModel(
            name='AJAXSectionDetail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('cls_id', models.IntegerField()),
                ('comment', models.CharField(max_length=256)),
                ('locked', models.BooleanField(default=False)),
                ('program', esp.db.fields.AjaxForeignKey(to='program.Program')),
            ],
        ),
        migrations.AddField(
            model_name='ajaxchangelogentry',
            name='comment',
            field=models.CharField(max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='ajaxchangelogentry',
            name='isScheduling',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='ajaxchangelogentry',
            name='locked',
            field=models.BooleanField(default=False),
        ),
    ]
