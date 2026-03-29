# Data migration to create the 'Waitlisted' RegistrationType
from django.db import migrations
def create_waitlisted_type(apps, schema_editor):
    RegistrationType = apps.get_model('program', 'RegistrationType')
    RegistrationType.objects.get_or_create(
        name='Waitlisted',
        defaults={'category': 'student', 'description': 'Waitlisted for a class section'},
    )
def remove_waitlisted_type(apps, schema_editor):
    RegistrationType = apps.get_model('program', 'RegistrationType')
    RegistrationType.objects.filter(name='Waitlisted').delete()
class Migration(migrations.Migration):
    dependencies = [
        ('program', '0030_auto_20260106_2204'),
    ]
    operations = [
        migrations.RunPython(create_waitlisted_type, remove_waitlisted_type),
    ]