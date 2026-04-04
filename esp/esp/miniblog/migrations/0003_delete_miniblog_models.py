from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('miniblog', '0002_auto_20151004_1715'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Comment',
        ),
        migrations.DeleteModel(
            name='Entry',
        ),
        migrations.DeleteModel(
            name='AnnouncementLink',
        ),
    ]
