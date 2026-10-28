"""Add start_date and end_date to ProgramModuleObj.

ProgramModuleObj now inherits from ExpirableModel.  We hand-write this
migration instead of auto-generating it so that **existing rows receive
NULL** for both columns (i.e. "always active / no expiry").

ExpirableModel defines ``start_date`` with ``default=datetime.now``.
An auto-generated migration would back-fill every existing module with
today's timestamp, which would break backward compatibility.  By
explicitly setting ``default=None`` here, Django's AddField populates
existing rows with NULL, which ``ExpirableModel.is_valid()`` treats as
"has always been valid".
"""

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0053_delete_mailinglabels'),
    ]

    operations = [
        migrations.AddField(
            model_name='programmoduleobj',
            name='start_date',
            field=models.DateTimeField(
                blank=True,
                null=True,
                default=None,
                help_text='If blank, has always started.',
            ),
        ),
        migrations.AddField(
            model_name='programmoduleobj',
            name='end_date',
            field=models.DateTimeField(
                blank=True,
                null=True,
                default=None,
                help_text='If blank, never ends.',
            ),
        ),
    ]
