# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.db import migrations, models
from esp.utils.cucumber import dump_python2_pickle, load_python2_pickle
import json


def resave_special_headers(apps, schema_editor):
    MessageRequest = apps.get_model('dbmail', 'MessageRequest')
    for mr in MessageRequest.objects.all():
        special_headers = load_python2_pickle(mr.special_headers)
        mr.special_headers = json.dumps(special_headers)
        mr.save()


def revert_special_headers(apps, schema_editor):
    MessageRequest = apps.get_model('dbmail', 'MessageRequest')
    for mr in MessageRequest.objects.all():
        special_headers = json.loads(mr.special_headers)
        mr.special_headers = dump_python2_pickle(special_headers)
        mr.save()


class Migration(migrations.Migration):
    dependencies = [
        ('dbmail', '0006_auto_20240309_0211'),
    ]
    operations = [
        migrations.RunPython(resave_special_headers, revert_special_headers),
    ]
