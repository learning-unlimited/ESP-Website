from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0042_classcategories_is_lunch'),
    ]

    operations = [
        migrations.AlterField(
            model_name='studentappreview',
            name='date',
            field=models.DateTimeField(default=django.utils.timezone.now, editable=False),
        ),
    ]
