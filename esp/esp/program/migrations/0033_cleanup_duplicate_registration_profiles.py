# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.db.models import Count, F
from django.db.migrations.exceptions import IrreversibleError


def cleanup_duplicate_profiles(apps, schema_editor):
    """
    Delete all duplicate registration profiles, keeping only the most recent
    profile for each (user, program) pair.

    This addresses the issue where before PR #2794, the system was creating
    new registration profiles nearly every time a user submitted the profile
    form, resulting in hundreds of duplicate profiles per user per program.
    """
    RegistrationProfile = apps.get_model('program', 'RegistrationProfile')

    # Find all (user_id, program_id) pairs that have more than one profile
    duplicates = RegistrationProfile.objects.values('user_id', 'program_id') \
        .annotate(count=Count('id')) \
        .filter(count__gt=1)

    deleted_count = 0
    user_program_pairs = 0

    print("\n" + "="*70)
    print("Starting cleanup of duplicate registration profiles...")
    print("="*70)

    for dup in duplicates:
        user_program_pairs += 1

        # Get all profiles for this user-program pair, ordered by most recent first
        # We order by -last_ts (most recent timestamp first), then by -id as a tiebreaker
        # Use nulls_last=True to ensure NULL timestamps are treated as oldest
        profiles = RegistrationProfile.objects.filter(
            user_id=dup['user_id'],
            program_id=dup['program_id']
        ).order_by(F('last_ts').desc(nulls_last=True), '-id')

        # Keep the first (most recent), delete the rest using a bulk delete
        keep_profile = profiles.first()
        if keep_profile is None:
            continue

        # Use the same queryset and exclude the kept profile for efficient bulk deletion
        profiles_to_delete_qs = profiles.exclude(pk=keep_profile.pk)
        deleted_for_pair, _ = profiles_to_delete_qs.delete()

        if deleted_for_pair > 0:
            print(f"User {dup['user_id']}, Program {dup['program_id']}: "
                  f"Deleting {deleted_for_pair} duplicate profile(s), keeping most recent")
            deleted_count += deleted_for_pair

    print("="*70)
    print(f"Cleanup complete!")
    print(f"  User-program pairs with duplicates: {user_program_pairs}")
    print(f"  Total duplicate profiles deleted: {deleted_count}")
    print("="*70 + "\n")


def reverse_migration(apps, schema_editor):
    """
    This migration cannot be reversed as we've permanently deleted data.
    This is intentional - we don't want to restore duplicate profiles.
    """
    raise IrreversibleError(
        "This migration cannot be reversed (duplicate data was permanently deleted)."
    )


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0032_auto_20260302_0348'),
    ]

    operations = [
        migrations.RunPython(cleanup_duplicate_profiles, reverse_migration),
    ]
