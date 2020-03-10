# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
import esp.program.modules.base

class Migration(migrations.Migration):
    dependencies = [
        ('modules', '0017_checkavailabilitymodule_finaidapprovemodule'),
    ]
    operations = [
        migrations.CreateModel(
            name='StudentOnsite',
            fields=[
            ],
            options={
                'proxy': True,
            },
            bases=('modules.programmoduleobj', esp.program.modules.base.CoreModule),
        ),
    ]
