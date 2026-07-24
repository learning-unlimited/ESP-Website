# Fixes Django system-check warning W340:
# W340: program.ClassSubject.allowable_class_size_ranges: null=True has no
# effect on a ManyToManyField. Remove it.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0040_printablejob'),
    ]

    operations = [
        migrations.AlterField(
            model_name='classsubject',
            name='allowable_class_size_ranges',
            field=models.ManyToManyField(
                blank=True,
                related_name='classsubject_allowedsizes',
                to='program.ClassSizeRange',
            ),
        ),
    ]
