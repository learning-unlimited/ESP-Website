# -*- coding: utf-8 -*-

from django.db import models, migrations
import esp.web.models
import esp.db.fields


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
        ('qsd', '0001_initial'),
        ('web', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='quasistaticdata',
            name='author',
            field=esp.db.fields.AjaxForeignKey(verbose_name='last modified by', to='users.ESPUser', on_delete=models.CASCADE),
        ),
        migrations.AddField(
            model_name='quasistaticdata',
            name='nav_category',
            field=models.ForeignKey(default=esp.web.models.default_navbarcategory, to='web.NavBarCategory', on_delete=models.CASCADE),
        ),
    ]
