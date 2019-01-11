# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import esp.program.modules.base

class Migration(migrations.Migration):
    dependencies = [
        ('modules', '0016_merge'),
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
