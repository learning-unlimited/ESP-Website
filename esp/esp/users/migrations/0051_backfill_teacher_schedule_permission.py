"""Grant the new Teacher/Classes/Schedule deadline to pre-existing programs.

Without this backfill, teachers of every existing program would silently lose
their room/time assignments as soon as Teacher/All expired at teacher_reg_end,
since only new programs get the permission seeded by prepare_program().
"""

from django.db import migrations

PERM = 'Teacher/Classes/Schedule'
#   Any program with one of these has teacher deadlines configured.
SOURCE_PERMS = ['Teacher/Classes/View', 'Teacher/MainPage', 'Teacher/All']


def add_schedule_permission(apps, schema_editor):
    Permission = apps.get_model('users', 'Permission')
    Group = apps.get_model('auth', 'Group')

    teacher_group = Group.objects.filter(name='Teacher').first()
    if teacher_group is None:
        #   No teacher role means no program has teacher deadlines either.
        return

    already_have = set(
        Permission.objects.filter(permission_type=PERM, program__isnull=False)
        .values_list('program_id', flat=True)
    )
    program_ids = set(
        Permission.objects.filter(
            permission_type__in=SOURCE_PERMS,
            program__isnull=False,
        ).values_list('program_id', flat=True)
    ) - already_have

    #   Default-open: start_date=None means "has always started", end_date=None
    #   means "never ends".  Admins close it while scheduling is in progress.
    Permission.objects.bulk_create([
        Permission(
            permission_type=PERM,
            program_id=program_id,
            role=teacher_group,
            start_date=None,
            end_date=None,
        )
        for program_id in sorted(program_ids)
    ], batch_size=100)


def remove_schedule_permission(apps, schema_editor):
    Permission = apps.get_model('users', 'Permission')
    Permission.objects.filter(permission_type=PERM).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0050_alter_permission_permission_type'),
        ('program', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_schedule_permission, remove_schedule_permission),
    ]
