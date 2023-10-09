# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import esp.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0022_auto_20210211_2303'),
    ]

    operations = [
        migrations.CreateModel(
            name='ESPUserData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('username', models.CharField(max_length=150)),
                ('referral_source', models.CharField(max_length=150, null=True)),
                ('referral_source_other', models.CharField(max_length=150, null=True)),
                ('user', esp.db.fields.AjaxForeignKey(to='users.ESPUser')),
            ],
            options={
                'db_table': 'users_espuserdata',
            },
        ),
    ]
