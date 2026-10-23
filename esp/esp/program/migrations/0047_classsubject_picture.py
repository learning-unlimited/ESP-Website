from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0046_classstatus_draft'),
    ]

    operations = [
        migrations.AddField(
            model_name='classsubject',
            name='picture',
            field=models.ImageField(blank=True, height_field='picture_height', null=True, upload_to='uploaded/class_pictures/%y_%m/', width_field='picture_width'),
        ),
        migrations.AddField(
            model_name='classsubject',
            name='picture_height',
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='classsubject',
            name='picture_width',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
