from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dbmail', '0013_auto_20260325_1833'),
    ]

    operations = [
        migrations.AddField(
            model_name='messagevars',
            name='provider_info',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='messagevars',
            name='pickled_provider',
            field=models.BinaryField(blank=True, null=True),
        ),
    ]
