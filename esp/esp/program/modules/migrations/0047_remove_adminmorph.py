from django.db import migrations

# Module-level list used to shuttle per-program M2M state from the forward
# migration to the reverse migration within a single manage.py invocation.
# If migrate is run in separate processes (uncommon) the reverse migration will
# restore only the registry row; per-program enablement cannot be recovered
# without this in-process capture.
_affected_program_ids = []


def remove_adminmorph_programmodule(apps, schema_editor):
    """
    Delete the ProgramModule registry entry for AdminMorph.
    Before deleting, record which programs had AdminMorph installed so that
    the reverse migration can restore those M2M links if needed.
    """
    ProgramModule = apps.get_model('program', 'ProgramModule')
    Program = apps.get_model('program', 'Program')

    adminmorph_qs = ProgramModule.objects.filter(handler='AdminMorph')
    if adminmorph_qs.exists():
        am_module = adminmorph_qs.get()
        # Capture per-program enablement before the cascade wipes the M2M rows.
        _affected_program_ids[:] = list(
            Program.objects.filter(modules=am_module).values_list('id', flat=True)
        )

    # Cascades to remove it from any Program.modules M2M relations automatically.
    adminmorph_qs.delete()


def restore_adminmorph_programmodule(apps, schema_editor):
    """
    Reverse of remove_adminmorph_programmodule.

    Re-inserts the ProgramModule registry entry and, when rolling back within
    the same process that ran the forward migration, also re-links every
    program that previously had AdminMorph installed.  If the forward migration
    ran in a separate process the M2M links cannot be recovered (the registry
    row is still restored, keeping the schema consistent).
    """
    ProgramModule = apps.get_model('program', 'ProgramModule')
    Program = apps.get_model('program', 'Program')

    am, _ = ProgramModule.objects.get_or_create(
        handler='AdminMorph',
        defaults={
            'link_title': 'Morph into User',
            'admin_title': 'User Morphing Capability',
            'module_type': 'manage',
            'seq': 34,
            'choosable': 1,
        },
    )

    # Restore per-program enablement captured by the forward migration.
    if _affected_program_ids:
        for program in Program.objects.filter(id__in=_affected_program_ids):
            program.modules.add(am)

class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0046_auto_20260106_2204'),
        ('program', '0001_initial'),
    ]

    operations = [
        # Clean up the ProgramModule registry row first (and any Program.modules M2M refs)
        migrations.RunPython(
            remove_adminmorph_programmodule,
            restore_adminmorph_programmodule,
        ),
        # Remove the Django proxy model
        migrations.DeleteModel(
            name='AdminMorph',
        ),
    ]
