from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0043_alter_phasezerorecord_program'),
    ]

    operations = [
        migrations.AlterField(
            model_name='classsection',
            name='status',
            field=models.IntegerField(choices=[(-20, 'cancelled'), (-10, 'rejected'), (-5, 'draft'), (0, 'unreviewed'), (5, 'accepted but hidden'), (10, 'accepted')], default=0),
        ),
        migrations.AlterField(
            model_name='classsubject',
            name='status',
            field=models.IntegerField(choices=[(-20, 'cancelled'), (-10, 'rejected'), (-5, 'draft'), (0, 'unreviewed'), (5, 'accepted but hidden'), (10, 'accepted')], default=0),
        ),
    ]
