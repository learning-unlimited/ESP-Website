from __future__ import unicode_literals
# -*- coding: utf-8 -*-
from django.db import migrations, models
from esp.utils.cucumber import load_python2_pickle
import json


def resave_special_headers(apps, schema_editor):
    MessageRequest = apps.get_model('dbmail', 'MessageRequest')
    for mr in MessageRequest.objects.all():
        special_headers = load_python2_pickle(mr.special_headers)
        mr.special_headers = json.dumps(special_headers)
        mr.save()


class Migration(migrations.Migration):
    dependencies = [
        ('dbmail', '0006_textofemail_user'),
    ]
    operations = [
        migrations.RunPython(resave_special_headers),
    ]
