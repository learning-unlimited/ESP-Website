# -*- coding: utf-8 -*-
from datetime import datetime

from django.db import migrations, models
from django.db.models import Count


def expire_duplicate_active_registrations(apps, schema_editor):
    """
    Expire duplicate active StudentRegistrations so the unique constraint added
    below can be applied.

    Sites that ran registration before the row locks in
    ClassSection.preregister_student() were in place can hold several rows with
    no end_date for the same (user, section, relationship).  The oldest row is
    the one that actually claimed the seat, so keep it and expire the rest;
    expiring rather than deleting preserves the registration history.
    """
    StudentRegistration = apps.get_model('program', 'StudentRegistration')
    now = datetime.now()

    duplicate_groups = (StudentRegistration.objects
                        .filter(end_date__isnull=True)
                        .values('user_id', 'section_id', 'relationship_id')
                        .annotate(num_rows=Count('id'))
                        .filter(num_rows__gt=1))

    for group in duplicate_groups.iterator():
        extra_ids = list(StudentRegistration.objects
                         .filter(end_date__isnull=True,
                                 user_id=group['user_id'],
                                 section_id=group['section_id'],
                                 relationship_id=group['relationship_id'])
                         .order_by('id')
                         .values_list('id', flat=True))[1:]
        StudentRegistration.objects.filter(id__in=extra_ids).update(end_date=now)


def noop_reverse(apps, schema_editor):
    """Removing the constraint is enough; the expired rows are left alone."""


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0043_alter_phasezerorecord_program'),
    ]

    operations = [
        migrations.RunPython(expire_duplicate_active_registrations, noop_reverse),
        migrations.AddConstraint(
            model_name='studentregistration',
            constraint=models.UniqueConstraint(
                condition=models.Q(('end_date__isnull', True)),
                fields=('user', 'section', 'relationship'),
                name='unique_active_enrollment',
            ),
        ),
    ]
