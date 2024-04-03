# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from __future__ import absolute_import
from django.db import migrations
from esp.utils.cucumber import dump_python2_pickle, load_python2_pickle


def resave_special_headers(apps, schema_editor):
    Answer = apps.get_model('survey', 'Answer')
    for ans in Answer.objects.all():
        ans.value = load_python2_pickle(ans.value)
        ans.save()


def revert_special_headers(apps, schema_editor):
    Answer = apps.get_model('survey', 'Answer')
    for ans in Answer.objects.all():
        ans.value = dump_python2_pickle(ans.value)
        ans.save()


class Migration(migrations.Migration):
    dependencies = [
        ('survey', '0002_auto_20200301_1048'),
    ]
    operations = [
        migrations.RunPython(resave_special_headers, revert_special_headers),
    ]
