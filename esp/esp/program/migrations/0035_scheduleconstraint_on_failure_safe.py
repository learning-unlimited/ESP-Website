# Generated manually for ScheduleConstraint on_failure field change

from django.db import migrations, models
from django.core.exceptions import ValidationError

def forwards(apps, schema_editor):
    ScheduleConstraint = apps.get_model('program', 'ScheduleConstraint')
    for obj in ScheduleConstraint.objects.all():
        old_value = obj.on_failure.strip().lower() if obj.on_failure else ''
        if 'retry' in old_value:
            obj.on_failure = 'retry'
        elif 'clear' in old_value:
            obj.on_failure = 'clear'
        else:
            obj.on_failure = 'noop'
        obj.save()

def backwards(apps, schema_editor):
    # Not reversible
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('program', '0034_auto_20260317_2119'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scheduleconstraint',
            name='on_failure',
            field=models.CharField(choices=[('noop', 'No operation'), ('retry', 'Retry once'), ('clear', 'Clear schedule')], default='noop', max_length=32),
        ),
        migrations.RunPython(forwards, backwards),
    ]