# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import absolute_import
from django.db import migrations
import pickle


def resave_special_headers(apps, schema_editor):
    Answer = apps.get_model('survey', 'Answer')
    for ans in Answer.objects.all():
        ans.value = pickle.loads(ans.value)
        ans.save()


def revert_special_headers(apps, schema_editor):
    Answer = apps.get_model('survey', 'Answer')
    for ans in Answer.objects.all():
        ans.value = pickle.dumps(ans.value)
        ans.save()


class Migration(migrations.Migration):
    dependencies = [
        ('survey', '0002_auto_20200301_1048'),
    ]
    operations = [
        migrations.RunPython(resave_special_headers, revert_special_headers),
    ]
