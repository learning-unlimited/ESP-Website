# Generated migration for Teacher Registration Custom Fields

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0012_auto_20170608_2205'),
    ]

    operations = [
        migrations.CreateModel(
            name='TeacherRegistrationCustomField',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('field_name', models.CharField(max_length=100, help_text='Unique identifier for this field (e.g., "qualifications")')),
                ('field_type', models.CharField(choices=[('text', 'Text Input'), ('textarea', 'Text Area'), ('integer', 'Integer'), ('float', 'Decimal Number'), ('boolean', 'Checkbox (True/False)'), ('select', 'Dropdown Select'), ('multiselect', 'Multiple Select'), ('radio', 'Radio Buttons'), ('email', 'Email Address'), ('url', 'URL')], default='text', max_length=20)),
                ('label', models.CharField(max_length=200, help_text='Display label for the field')),
                ('help_text', models.TextField(blank=True, help_text='Help text shown below the field')),
                ('required', models.BooleanField(default=False, help_text='Whether this field is required')),
                ('position', models.IntegerField(default=0, help_text='Display order (lower numbers appear first)')),
                ('choices', models.TextField(blank=True, help_text='Comma-separated choices for dropdown/radio fields')),
                ('max_length', models.IntegerField(blank=True, help_text='Maximum character length for text fields', null=True)),
                ('min_value', models.FloatField(blank=True, help_text='Minimum value for number fields', null=True)),
                ('max_value', models.FloatField(blank=True, help_text='Maximum value for number fields', null=True)),
                ('is_visible', models.BooleanField(default=True, help_text='Whether this field is shown on the form')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='teacher_custom_fields', to='program.Program')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.ESPUser')),
            ],
            options={
                'verbose_name': 'Teacher Registration Custom Field',
                'verbose_name_plural': 'Teacher Registration Custom Fields',
                'ordering': ['position', 'label'],
                'unique_together': {('program', 'field_name')},
            },
        ),
        migrations.CreateModel(
            name='TeacherRegistrationCustomFieldValue',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('class_subject_id', models.IntegerField(help_text='ID of the ClassSubject')),
                ('value', models.TextField(blank=True, help_text='The value submitted for this field')),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='values', to='program.TeacherRegistrationCustomField')),
            ],
            options={
                'verbose_name': 'Teacher Registration Custom Field Value',
                'verbose_name_plural': 'Teacher Registration Custom Field Values',
                'unique_together': {('field', 'class_subject_id')},
            },
        ),
    ]
