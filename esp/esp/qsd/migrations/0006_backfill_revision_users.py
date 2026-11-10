# -*- coding: utf-8 -*-
"""Fill in the user on old QSD revisions from each version's own `author`.

Until 2026-11, QSD edits made on the site (rather than in the admin panel)
created reversion revisions with no user, though every QSD snapshot records
its author.  Revisions whose author no longer exists are left alone.
"""
from __future__ import unicode_literals

from collections import defaultdict
import json

from django.conf import settings
from django.db import migrations

CHUNK_SIZE = 1000


def backfill_revision_users(apps, schema_editor):
    ContentType = apps.get_model('contenttypes', 'ContentType')
    Revision = apps.get_model('reversion', 'Revision')
    Version = apps.get_model('reversion', 'Version')
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))

    content_type = ContentType.objects.filter(app_label='qsd', model='quasistaticdata').first()
    if content_type is None:
        return
    user_ids = set(User.objects.values_list('id', flat=True))
    revisions_by_user = defaultdict(list)
    versions = Version.objects.filter(content_type=content_type, revision__user__isnull=True)
    for revision_id, data in versions.values_list('revision_id', 'serialized_data').iterator():
        try:
            author = json.loads(data)[0]['fields'].get('author')
        except (ValueError, LookupError, TypeError, AttributeError):
            continue
        if author in user_ids:
            revisions_by_user[author].append(revision_id)
    for user_id, revision_ids in revisions_by_user.items():
        for start in range(0, len(revision_ids), CHUNK_SIZE):
            Revision.objects.filter(id__in=revision_ids[start:start + CHUNK_SIZE], user__isnull=True).update(user_id=user_id)


class Migration(migrations.Migration):

    dependencies = [
        ('qsd', '0005_qsd_url_unique'),
        ('reversion', '0002_auto_20141216_1509'),
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(backfill_revision_users, migrations.RunPython.noop),
    ]
