import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0043_alter_phasezerorecord_program'),
    ]

    operations = [
        migrations.AlterField(
            model_name='program',
            name='name',
            field=models.CharField(
                help_text='The full name of this program (e.g. Splash Fall 2007).',
                max_length=80,
                validators=[
                    django.core.validators.RegexValidator(
                        message='Program name may not contain control characters or the characters "<" and ">".',
                        regex='\\A[^<>\\x00-\\x1f\\x7f]+\\Z',
                    )
                ],
            ),
        ),
        migrations.AlterField(
            model_name='program',
            name='url',
            field=models.CharField(
                help_text='The URL fragment for this program, of the form ProgramType/Term (e.g. Splash/2007_Fall).',
                max_length=80,
                unique=True,
                validators=[
                    django.core.validators.RegexValidator(
                        message='Program URL must have the form ProgramType/Term (e.g. Splash/2007_Fall) and may only contain letters, numbers, spaces, underscores, and hyphens.',
                        regex='\\A[A-Za-z0-9_ -]+/[A-Za-z0-9_ -]+\\Z',
                    )
                ],
            ),
        ),
    ]
