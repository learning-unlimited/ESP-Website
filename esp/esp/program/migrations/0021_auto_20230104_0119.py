# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0020_auto_20210211_2303'),
    ]

    operations = [
        migrations.AlterField(
            model_name='program',
            name='director_email',
            field=models.EmailField(help_text=b'The "director email" should be the public-facing email address for the program (e.g. splash@mit.edu). It should usually <i>not</i> be a directors-only email address.', max_length=75),
        ),
    ]
