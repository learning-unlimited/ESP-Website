# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from __future__ import absolute_import
import json
from collections import defaultdict

from django.db import migrations


def backfill_postbacks(apps, schema_editor):
    """ Fill in user, program, and transaction_id for existing postbacks
    from their stored POST data. The identifier we send to Cybersource
    (echoed back as req_merchant_defined_data1) starts with
    '<program id>/<user id>:'. Postbacks that can't be parsed, or that name
    a user or program that no longer exists, are left blank. """
    CybersourcePostback = apps.get_model('accounting', 'CybersourcePostback')
    ESPUser = apps.get_model('users', 'ESPUser')
    Program = apps.get_model('program', 'Program')

    parsed = {}
    for pk, post_data in CybersourcePostback.objects.values_list('id', 'post_data').iterator():
        try:
            data = json.loads(post_data)
        except ValueError:
            continue
        if not isinstance(data, dict):
            continue
        program_id = user_id = None
        try:
            program_str, user_str = data.get('req_merchant_defined_data1', '').split(':')[0].split('/')
            program_id, user_id = int(program_str), int(user_str)
        except (ValueError, AttributeError):
            pass
        transaction_id = data.get('transaction_id') or ''
        if not isinstance(transaction_id, str):
            transaction_id = ''
        parsed[pk] = (program_id, user_id, transaction_id[:64])

    user_ids = set(ESPUser.objects.filter(
        id__in={u for (_, u, _) in parsed.values() if u}).values_list('id', flat=True))
    program_ids = set(Program.objects.filter(
        id__in={p for (p, _, _) in parsed.values() if p}).values_list('id', flat=True))

    groups = defaultdict(list)
    for pk, (program_id, user_id, transaction_id) in parsed.items():
        key = (program_id if program_id in program_ids else None,
               user_id if user_id in user_ids else None)
        if key != (None, None):
            groups[key].append(pk)
        if transaction_id:
            CybersourcePostback.objects.filter(id=pk).update(transaction_id=transaction_id)
    for (program_id, user_id), pks in groups.items():
        for i in range(0, len(pks), 1000):
            CybersourcePostback.objects.filter(id__in=pks[i:i + 1000]).update(
                program_id=program_id, user_id=user_id)


class Migration(migrations.Migration):
    """ Backfill the fields added in 0017. Kept separate from 0017 so the data
    updates run in their own transaction: on Postgres, updating rows in the
    same transaction that adds a foreign key leaves deferred constraint
    checks pending, and creating that field's index then fails. """

    dependencies = [
        ('accounting', '0017_cybersourcepostback_status'),
        # backfill_postbacks looks up users and programs (by id only)
        ('program', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(backfill_postbacks, migrations.RunPython.noop),
    ]
