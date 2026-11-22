from django.db import migrations, models


def progress_mode_to_show_checklist(apps, schema_editor):
    # 1 (checklist) and 2 (former progress bar, now the same checklist) show it; 0 doesn't.
    for model_name in ('ClassRegModuleInfo', 'StudentClassRegModuleInfo'):
        model = apps.get_model('modules', model_name)
        model.objects.filter(progress_mode=0).update(show_checklist=False)


def show_checklist_to_progress_mode(apps, schema_editor):
    for model_name in ('ClassRegModuleInfo', 'StudentClassRegModuleInfo'):
        model = apps.get_model('modules', model_name)
        model.objects.filter(show_checklist=False).update(progress_mode=0)


class Migration(migrations.Migration):

    dependencies = [
        ("modules", "0057_studentclassregmoduleinfo_progress_mode_help"),
    ]

    operations = [
        migrations.AddField(
            model_name="classregmoduleinfo",
            name="show_checklist",
            field=models.BooleanField(
                default=True,
                help_text="Check this box to show the registration checklist (the registration steps, with a progress bar) on the teacher registration pages.",
            ),
        ),
        migrations.AddField(
            model_name="studentclassregmoduleinfo",
            name="show_checklist",
            field=models.BooleanField(
                default=True,
                help_text="Check this box to show the registration checklist (the registration steps, with a progress bar) on the student registration pages.",
            ),
        ),
        migrations.RunPython(progress_mode_to_show_checklist, show_checklist_to_progress_mode),
        migrations.RemoveField(
            model_name="classregmoduleinfo",
            name="progress_mode",
        ),
        migrations.RemoveField(
            model_name="studentclassregmoduleinfo",
            name="progress_mode",
        ),
    ]
