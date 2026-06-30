# -*- coding: utf-8 -*-
# Teacher email validation rules per program (Issue #3639)

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('modules', '0047_programmoduleobj_link_title'),
        ('program', '0030_auto_20260106_2204'),
    ]

    operations = [
        migrations.CreateModel(
            name='TeacherEmailRules',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('enabled', models.BooleanField(default=False, help_text='Enable teacher email validation for this program. When enabled, teacher emails are checked against the allowed domains and/or regex below.')),
                ('allowed_domains', models.TextField(blank=True, help_text='Comma-separated list of allowed email domains (e.g. school.edu, university.edu). Case-insensitive. Leave blank to not restrict by domain.')),
                ('regex_pattern', models.CharField(blank=True, help_text='Optional regex pattern the full email must match (e.g. .*@school\\.edu$). Leave blank to not use regex. If both domains and regex are set, email must match either.', max_length=255)),
                ('mode', models.CharField(choices=[('block', 'Block (reject non-matching emails)'), ('warn', 'Warn only (show notice but allow)')], default='warn', help_text='Block: reject signup/profile save if email does not match. Warn: show a notice but allow the email.', max_length=10)),
                ('program', models.OneToOneField(on_delete=models.CASCADE, related_name='teacher_email_rules', to='program.Program')),
            ],
            options={
                'verbose_name': 'Teacher email rules',
                'verbose_name_plural': 'Teacher email rules',
                'db_table': 'modules_teacheremailrules',
            },
        ),
    ]
