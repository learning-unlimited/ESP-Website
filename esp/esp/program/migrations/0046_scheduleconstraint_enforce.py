from django.db import migrations, models


def enforce_existing_constraints(apps, schema_editor):
    """ Programs that already have constraints were blocking on them, so keep
    doing that; the new advisory default only applies to constraints created
    from here on. """
    ScheduleConstraint = apps.get_model('program', 'ScheduleConstraint')
    ScheduleConstraint.objects.update(enforce=True)


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0045_backfill_studentappreview_class_subject'),
    ]

    operations = [
        migrations.AddField(
            model_name='scheduleconstraint',
            name='enforce',
            field=models.BooleanField(default=False, help_text='Prevent schedule changes that would newly violate this constraint, rather than only warning about it'),
        ),
        #   Reverse is a noop: unmigrating drops the column anyway.
        migrations.RunPython(enforce_existing_constraints, migrations.RunPython.noop),
    ]
