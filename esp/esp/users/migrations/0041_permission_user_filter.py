from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0040_auto_20260106_2204'),
    ]

    operations = [
        migrations.AddField(
            model_name='permission',
            name='user_filter',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to='users.PersistentQueryFilter',
                help_text='Apply this permission to all users matching this saved filter.',
            ),
        ),
    ]

