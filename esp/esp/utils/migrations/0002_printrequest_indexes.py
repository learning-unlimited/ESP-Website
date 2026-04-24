# -*- coding: utf-8 -*-

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Add partial composite indexes to PrintRequest for queue performance.

    Both indexes are filtered to rows where time_executed IS NULL,
    so they cover only pending/unexecuted print jobs rather than the
    full historical table — keeping them small and fast.

    Index 1 (pr_exec_req_idx):
        Supports the global pending-queue poll:
            PrintRequest.objects.filter(time_executed__isnull=True)
                                .order_by('time_requested', 'id')

    Index 2 (pr_printer_exec_req_idx):
        Supports the per-printer pending-queue poll:
            PrintRequest.objects.filter(time_executed__isnull=True,
                                        printer__name=<name>)
                                .order_by('time_requested', 'id')

    Requires PostgreSQL (partial indexes are a PostgreSQL feature).
    See: https://docs.djangoproject.com/en/stable/ref/models/indexes/#condition
    """

    dependencies = [
        ('utils', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='printrequest',
            index=models.Index(
                fields=['time_requested', 'id'],
                name='pr_exec_req_idx',
                condition=models.Q(time_executed__isnull=True),
            ),
        ),
        migrations.AddIndex(
            model_name='printrequest',
            index=models.Index(
                fields=['printer', 'time_requested', 'id'],
                name='pr_printer_exec_req_idx',
                condition=models.Q(time_executed__isnull=True),
            ),
        ),
    ]
