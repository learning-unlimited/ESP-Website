# Fixes Django system-check warning W340:
# W340: program.ClassSubject.allowable_class_size_ranges: null=True has no
# effect on a ManyToManyField. Remove it.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("program", "0047_alter_program_name_alter_program_url"),
    ]

    operations = [
        migrations.AlterField(
            model_name="classsubject",
            name="allowable_class_size_ranges",
            field=models.ManyToManyField(
                blank=True,
                related_name="classsubject_allowedsizes",
                to="program.classsizerange",
            ),
        ),
    ]
