# Generated manually to sync help_text with models (no DB schema change).

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('application', '0009_auto_20260106_2204'),
    ]

    operations = [
        migrations.AlterField(
            model_name='formstackappsettings',
            name='autopopulated_fields',
            field=models.TextField(blank=True, help_text="""\
To autopopulate fields on the form, type "[field id]: [value expression]",
one field per line, using a colon separator. The expression can use the
variable 'user' to refer to request.user.

Use Django template syntax for values, for example: 12345: {{ user.username }}

For backwards compatibility, dotted lookups without braces are also accepted,
for example: 12345: user.username"""),
        ),
    ]
