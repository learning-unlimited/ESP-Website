# -*- coding: utf-8 -*-

from django.db import models, migrations
import esp.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('resources', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='resource',
            name='user',
            field=esp.db.fields.AjaxForeignKey(blank=True, to='users.ESPUser', null=True, on_delete=models.CASCADE),
        ),
    ]
