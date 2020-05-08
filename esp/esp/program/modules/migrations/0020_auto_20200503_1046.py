# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import esp.program.modules.base


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0019_auto_20200502_1251'),
    ]

    operations = [
        migrations.RenameModel('CreditCardViewer_Cybersource', 'CreditCardViewer')
    ]
