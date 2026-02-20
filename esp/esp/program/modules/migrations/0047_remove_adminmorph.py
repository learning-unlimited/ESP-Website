from django.db import migrations


def remove_adminmorph_programmodule(apps, schema_editor):
    """
    Delete the ProgramModule registry entry for AdminMorph.
    This cascades to remove it from any Program.modules M2M relations
    so programs that had this module installed are automatically cleaned up.
    """
    ProgramModule = apps.get_model('program', 'ProgramModule')
    ProgramModule.objects.filter(handler='AdminMorph').delete()


def restore_adminmorph_programmodule(apps, schema_editor):
    """
    Reverse of remove_adminmorph_programmodule.
    Re-inserts the ProgramModule registry entry for AdminMorph so that
    rolling back this migration leaves the database consistent with the
    code present before this migration was applied.
    """
    ProgramModule = apps.get_model('program', 'ProgramModule')
    ProgramModule.objects.get_or_create(
        handler='AdminMorph',
        defaults={
            'link_title': 'Morph into User',
            'admin_title': 'User Morphing Capability',
            'module_type': 'manage',
            'seq': 34,
            'choosable': 1,
        },
    )

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
