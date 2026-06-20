# Migration: widen address_zip (5→10) to support ZIP+4 format (e.g. "12345-6789")
# and address_postcode (10→12) for extra headroom on uncommon international formats.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0046_contactinfo_address_postcode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contactinfo',
            name='address_zip',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='Zip code'),
        ),
        migrations.AlterField(
            model_name='contactinfo',
            name='address_postcode',
            field=models.CharField(blank=True, max_length=12, null=True, verbose_name='Postcode'),
        ),
    ]
