# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models

def migrate_answers(apps, schema_editor):
    Answer = apps.get_model('survey', 'Answer')
    for answer in Answer.objects.all():
        val = answer.value
        if val.startswith(":"):
            answer.value = val[1:]
            # default value_type is already str
        elif val.startswith("+"):
            answer.value = val[1:]
            answer.value_type == "<class 'list'>"
        answer.save()

class Migration(migrations.Migration):

    dependencies = [
        ('survey', '0004_answer_value_type'),
    ]

    operations = [
        migrations.RunPython(migrate_answers, migrations.RunPython.noop),
    ]
