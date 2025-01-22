# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import absolute_import
from django.db import migrations, models
import json
import pickle


def resave_special_headers(apps, schema_editor):
    MessageRequest = apps.get_model('dbmail', 'MessageRequest')
    for mr in MessageRequest.objects.all():
        if mr.special_headers != None and mr.special_headers != '':
            special_headers = pickle.loads(mr.special_headers.replace('\r\n', '\n').encode('latin1'))
            mr.special_headers = json.dumps(special_headers)
            mr.save()


def revert_special_headers(apps, schema_editor):
    MessageRequest = apps.get_model('dbmail', 'MessageRequest')
    for mr in MessageRequest.objects.all():
        special_headers = json.loads(mr.special_headers)
        mr.special_headers = pickle.dumps(special_headers)
        mr.save()


class Migration(migrations.Migration):
    dependencies = [
        ('dbmail', '0006_auto_20240309_1411'),
    ]
    operations = [
        migrations.RunPython(resave_special_headers, revert_special_headers),
    ]
