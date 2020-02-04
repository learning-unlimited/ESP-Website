# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0008_auto_20151228_0043'),
    ]

    operations = [
        migrations.CreateModel(
            name='CybersourcePostback',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('post_data', models.TextField()),
                ('transfer', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, to='accounting.Transfer', null=True)),
            ],
        ),
    ]
