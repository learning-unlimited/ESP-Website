# Migration: add address_postcode to ContactInfo (GitHub issue #5845).
# This supports international addresses where zip codes do not apply
# (e.g. UK postcodes like "SW1A 1AA" which are up to 8 characters long).
# address_zip (max 5 chars) remains for US addresses; address_postcode (max 10 chars)
# is used instead when the user selects "International" from the state dropdown.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0045_k12school_city_k12school_state_alter_k12school_name_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='contactinfo',
            name='address_postcode',
            field=models.CharField(blank=True, max_length=10, null=True, verbose_name='Postcode'),
        ),
    ]
