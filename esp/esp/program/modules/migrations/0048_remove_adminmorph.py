from django.db import migrations


def remove_adminmorph_programmodule(apps, schema_editor):
    """
    Delete the ProgramModule registry entry for AdminMorph.
    This cascades to remove it from any Program.modules M2M relations
    so programs that had this module installed are automatically cleaned up.
    """
    ProgramModule = apps.get_model('program', 'ProgramModule')
    ProgramModule.objects.filter(handler='AdminMorph').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0047_programmoduleobj_link_title'),
        ('program', '0001_initial'),
    ]

    operations = [
        # Clean up the ProgramModule registry row first (and any Program.modules M2M refs)
        migrations.RunPython(
            remove_adminmorph_programmodule,
            migrations.RunPython.noop,
        ),
        # Remove the Django proxy model
        migrations.DeleteModel(
            name='AdminMorph',
        ),
    ]
