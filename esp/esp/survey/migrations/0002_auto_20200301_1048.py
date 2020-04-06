# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

def create_question_types(apps, schema_editor):
    db_alias = schema_editor.connection.alias
    QuestionType = apps.get_model("survey", "QuestionType")
    QuestionType.objects.using(db_alias).get_or_create(name="Instruction Text", _param_names = "Text")
    QuestionType.objects.using(db_alias).get_or_create(name="Long Answer", _param_names = "Rows")
    QuestionType.objects.using(db_alias).get_or_create(name="Short Answer", _param_names = "Input length")
    QuestionType.objects.using(db_alias).get_or_create(name="Labeled Numeric Rating", _param_names = "Number of ratings", is_numeric=True, is_countable=True)
    QuestionType.objects.using(db_alias).get_or_create(name="Numeric Rating", _param_names = "Number of ratings|Lower text|Middle text|Upper text", is_numeric=True, is_countable=True)
    QuestionType.objects.using(db_alias).get_or_create(name="Checkboxes", is_countable=True)
    QuestionType.objects.using(db_alias).get_or_create(name="Multiple Choice", is_countable=True)
    QuestionType.objects.using(db_alias).get_or_create(name="Yes-No Response", is_countable=True)
    QuestionType.objects.using(db_alias).get_or_create(name="Favorite Class")

class Migration(migrations.Migration):

    dependencies = [
        ('survey', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_question_types),
    ]
