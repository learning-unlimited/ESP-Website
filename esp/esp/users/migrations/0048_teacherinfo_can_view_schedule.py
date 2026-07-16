from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0047_alter_permission_user_filter'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacherinfo',
            name='can_view_schedule',
            field=models.BooleanField(default=True),
        ),
    ]
