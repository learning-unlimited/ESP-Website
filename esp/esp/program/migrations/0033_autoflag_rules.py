# Generated manually on 2026-03-11

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('program', '0032_auto_20260302_0348'),
    ]

    operations = [
        migrations.CreateModel(
            name='AutoClassFlagRule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rule_data', models.TextField(help_text='JSON representation of the QueryBuilder rule')),
                ('comment', models.TextField(blank=True, help_text='Annotation/comment to add to the flag')),
                ('flag_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='program.ClassFlagType')),
                ('program', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='autoflag_rules', to='program.Program')),
            ],
        ),
    ]
