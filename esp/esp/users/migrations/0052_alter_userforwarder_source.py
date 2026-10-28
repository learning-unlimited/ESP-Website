# Fixes Django system-check warning W342:
# W342: users.UserForwarder.source: Setting unique=True on a ForeignKey has
# the same effect as using a OneToOneField. Use OneToOneField instead.

import django.db.models.deletion
import esp.db.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0051_backfill_teacher_schedule_permission"),
    ]

    operations = [
        migrations.AlterField(
            model_name="userforwarder",
            name="source",
            field=esp.db.fields.AjaxOneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="forwarders_out",
                to="users.espuser",
            ),
        ),
    ]
