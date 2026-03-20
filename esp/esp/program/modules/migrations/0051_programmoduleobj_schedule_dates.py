from datetime import datetime

from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Adds start_date and end_date to ProgramModuleObj (issues #3854 / #2895).
    Both fields nullable so existing modules remain perpetually active.
    """

    dependencies = [
        ('modules', '0050_merge_20260307_0349'),
    ]

    operations = [
        migrations.AddField(
            model_name='programmoduleobj',
            name='start_date',
            field=models.DateTimeField(
                blank=True,
                null=True,
                default=datetime.now,
                help_text='If blank, has always started.',
            ),
        ),
        migrations.AddField(
            model_name='programmoduleobj',
            name='end_date',
            field=models.DateTimeField(
                blank=True,
                null=True,
                default=None,
                help_text='If blank, never ends.',
            ),
        ),
    ]