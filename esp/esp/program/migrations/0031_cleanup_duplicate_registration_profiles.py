# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations
from django.db.models import Count


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
        profiles = RegistrationProfile.objects.filter(
            user_id=dup['user_id'],
            program_id=dup['program_id']
        ).order_by('-last_ts', '-id')
        
        # Keep the first (most recent), delete the rest
        profiles_to_delete = list(profiles[1:])
        count = len(profiles_to_delete)
        
        if count > 0:
            print(f"User {dup['user_id']}, Program {dup['program_id']}: "
                  f"Deleting {count} duplicate profile(s), keeping most recent")
            
            # Delete the duplicates
            for profile in profiles_to_delete:
                profile.delete()
            
            deleted_count += count
    
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
    print("This migration cannot be reversed (duplicate data was permanently deleted).")


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0030_auto_20260106_2204'),
    ]

    operations = [
        migrations.RunPython(cleanup_duplicate_profiles, reverse_migration),
    ]
