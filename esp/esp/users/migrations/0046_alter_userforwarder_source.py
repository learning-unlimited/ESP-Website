# Fixes Django system-check warning W342:
# W342: users.UserForwarder.source: Setting unique=True on a ForeignKey has
# the same effect as using a OneToOneField. Use OneToOneField instead.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('users', '0044_alter_contactinfo_address_country'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userforwarder',
            name='source',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='forwarders_out',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
