import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0043_alter_phasezerorecord_program'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentappreview',
            name='class_subject',
            field=models.ForeignKey(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='program.classsubject'),
        ),
    ]
