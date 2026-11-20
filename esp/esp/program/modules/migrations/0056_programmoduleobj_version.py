# Generated manually for timeline undo/redo OCC

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0055_split_regprofilemodule'),
    ]

    operations = [
        migrations.AddField(
            model_name='programmoduleobj',
            name='version',
            field=models.PositiveIntegerField(default=1),
        ),
    ]
