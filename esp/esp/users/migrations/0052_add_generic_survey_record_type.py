from django.db import migrations

def create_generic_survey_event(apps, schema_editor):
    RecordType = apps.get_model('users', 'RecordType')
    RecordType.objects.get_or_create(
        name='generic_survey',
        defaults={'description': 'Completed generic survey'}
    )

def delete_generic_survey_event(apps, schema_editor):
    RecordType = apps.get_model('users', 'RecordType')
    RecordType.objects.filter(name='generic_survey').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0051_backfill_teacher_schedule_permission'),
    ]

    operations = [
        migrations.RunPython(create_generic_survey_event, delete_generic_survey_event),
    ]
