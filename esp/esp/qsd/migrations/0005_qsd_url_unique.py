# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


def dedupe_qsd_urls(apps, schema_editor):
    """
    Before django-reversion existed, editing a QSD page could leave behind
    multiple rows sharing the same url (each edit inserted a new row instead
    of updating in place). Reversion now tracks edit history on its own, so
    for any url with more than one surviving row, keep only the one that
    get_by_url() would already pick as "latest" (by create_date, then id) and
    drop the rest -- they are unreachable through the app today regardless,
    since every read path already only ever surfaces the latest row.
    """
    QuasiStaticData = apps.get_model('qsd', 'QuasiStaticData')
    seen_urls = set()
    for qsd in QuasiStaticData.objects.order_by('-create_date', '-id'):
        if qsd.url in seen_urls:
            qsd.delete()
        else:
            seen_urls.add(qsd.url)


def reverse_func(apps, schema_editor):
    # Deleted duplicate rows can't be un-deleted; nothing to do.
    return


class Migration(migrations.Migration):

    dependencies = [
        ('qsd', '0004_clean_class_qsds'),
    ]

    operations = [
        migrations.RunPython(dedupe_qsd_urls, reverse_func),
        migrations.AlterField(
            model_name='quasistaticdata',
            name='url',
            field=models.CharField(help_text='Full url, without the trailing .html', max_length=256, unique=True),
        ),
    ]
