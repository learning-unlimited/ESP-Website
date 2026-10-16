from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0046_scheduleconstraint_enforce'),
    ]

    operations = [
        #   on_failure stored Python source that was exec()'d on constraint
        #   failure.  The behaviour it implemented is now a boolean plus real
        #   code; see esp.program.models.autocorrect_schedule.
        migrations.RemoveField(
            model_name='scheduleconstraint',
            name='on_failure',
        ),
        migrations.AddField(
            model_name='scheduleconstraint',
            name='autocorrect',
            field=models.BooleanField(default=False, help_text='Should the student be enrolled automatically in something that satisfies this constraint, rather than being warned or blocked?'),
        ),
    ]
