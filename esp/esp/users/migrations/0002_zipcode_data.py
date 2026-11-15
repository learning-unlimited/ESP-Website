# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
from decimal import Decimal
import json
import os

from django.core.management.color import no_style
from django.db import models, migrations

BATCH_SIZE = 5000

def import_zipcodes(apps, schema_editor):
    """ Load the zip codes in the fixture with bulk inserts.

    This used to run loaddata on the fixture, which saves one row at a time
    (an UPDATE then an INSERT for each of ~42,000 rows) and was about half
    the time it takes to build a fresh database, e.g. for every test run.
    The rows, including their ids, are the same.
    """
    ZipCode = apps.get_model('users', 'ZipCode')
    fixture_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
                                                '..', 'fixtures', 'initial_zipcode_data.json'))
    with open(fixture_path) as f:
        rows = json.load(f)
    zipcodes = [ZipCode(id=row['pk'],
                        zip_code=row['fields']['zip_code'],
                        latitude=Decimal(row['fields']['latitude']),
                        longitude=Decimal(row['fields']['longitude']))
                for row in rows]
    db_alias = schema_editor.connection.alias
    ZipCode.objects.using(db_alias).bulk_create(zipcodes, batch_size=BATCH_SIZE)

    # The rows have explicit ids, so move the id sequence past them, as
    # loaddata did.
    with schema_editor.connection.cursor() as cursor:
        for sql in schema_editor.connection.ops.sequence_reset_sql(no_style(), [ZipCode]):
            cursor.execute(sql)

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        # This will run backwards, but won't do anything
        migrations.RunPython(import_zipcodes, lambda a, s: None)
    ]
