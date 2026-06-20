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
