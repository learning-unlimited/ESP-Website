# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import esp.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('dbmail', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='messagerequest',
            name='creator',
            field=esp.db.fields.AjaxForeignKey(to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='messagerequest',
            name='recipients',
            field=models.ForeignKey(to='users.PersistentQueryFilter'),
        ),
        migrations.AddField(
            model_name='emailrequest',
            name='msgreq',
            field=models.ForeignKey(to='dbmail.MessageRequest'),
        ),
        migrations.AddField(
            model_name='emailrequest',
            name='target',
            field=esp.db.fields.AjaxForeignKey(to='users.ESPUser'),
        ),
        migrations.AddField(
            model_name='emailrequest',
            name='textofemail',
            field=esp.db.fields.AjaxForeignKey(blank=True, to='dbmail.TextOfEmail', null=True),
        ),
    ]
