# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management import call_command
from django.db import models, migrations

import os

def import_zipcodes(apps, schema_editor):
    fixture_label = os.path.join(os.path.dirname(__file__),
                                 '..',
                                 'fixtures',
                                 'initial_zipcode_data.json')
    fixture_label = os.path.abspath(fixture_label)
    call_command('loaddata', fixture_label, verbosity=1)

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        # This will run backwards, but won't do anything
        migrations.RunPython(import_zipcodes, lambda a, s: None)
    ]
