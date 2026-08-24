import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0043_alter_phasezerorecord_program'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentappreview',
            name='date',
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
    ]
