# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import esp.program.modules.base


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0018_studentonsite'),
    ]

    operations = [
        migrations.RenameModel('CreditCardViewer_Cybersource', 'CreditCardViewer')
    ]
