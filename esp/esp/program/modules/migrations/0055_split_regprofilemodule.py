# Generated manually for splitting RegProfileModule

from django.db import migrations


def split_regprofilemodule(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')

    # Split learn modules
    ProgramModule.objects.filter(
        handler='RegProfileModule',
        module_type='learn'
    ).update(handler='StudentRegProfileModule')

    # Split teach modules
    ProgramModule.objects.filter(
        handler='RegProfileModule',
        module_type='teach'
    ).update(handler='TeacherRegProfileModule')


def reverse_split(apps, schema_editor):
    ProgramModule = apps.get_model('program', 'ProgramModule')

    ProgramModule.objects.filter(
        handler='StudentRegProfileModule'
    ).update(handler='RegProfileModule')

    ProgramModule.objects.filter(
        handler='TeacherRegProfileModule'
    ).update(handler='RegProfileModule')


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0054_programmoduleobj_expirable'),
    ]

    operations = [
        migrations.DeleteModel(
            name='RegProfileModule',
        ),
        migrations.CreateModel(
            name='StudentRegProfileModule',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('modules.programmoduleobj',),
        ),
        migrations.CreateModel(
            name='TeacherRegProfileModule',
            fields=[
            ],
            options={
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('modules.programmoduleobj',),
        ),
        migrations.RunPython(split_regprofilemodule, reverse_split),
    ]
