# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import esp.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('miniblog', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='entry',
            name='fromuser',
            field=esp.db.fields.AjaxForeignKey(blank=True, editable=False, to='users.ESPUser', null=True),
        ),
        migrations.AddField(
            model_name='comment',
            name='author',
            field=esp.db.fields.AjaxForeignKey(to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='comment',
            name='entry',
            field=models.ForeignKey(to='miniblog.Entry'),
        ),
    ]
