# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='EmailList',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('regex', models.CharField(help_text=b"(e.g. '^(.*)$' matches everything)", max_length=512, verbose_name=b'Regular Expression')),
                ('seq', models.PositiveIntegerField(help_text=b'Smaller is earlier.', verbose_name=b'Sequence', blank=True)),
                ('handler', models.CharField(max_length=128)),
                ('subject_prefix', models.CharField(max_length=64, null=True, blank=True)),
                ('admin_hold', models.BooleanField(default=False)),
                ('cc_all', models.BooleanField(default=False, help_text=b'If true, the CC field will list everyone. Otherwise each email will be sent individually.')),
                ('from_email', models.CharField(help_text=b'If specified, the FROM header will be overwritten with this email.', max_length=512, null=True, blank=True)),
                ('description', models.TextField(null=True, blank=True)),
            ],
            options={
                'ordering': ('seq',),
            },
        ),
        migrations.CreateModel(
            name='EmailRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='MessageRequest',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True)),
                ('subject', models.TextField(null=True, blank=True)),
                ('msgtext', models.TextField(null=True, blank=True)),
                ('special_headers', models.TextField(null=True, blank=True)),
                ('sendto_fn_name', models.CharField(default=b'', help_text=b'The function that specifies, for each recipient of the message, which set of associated email addresses should receive the message.', max_length=128, verbose_name=b'sendto function', choices=[(b'', b'send to user'), (b'send_to_guardian', b'send to guardian'), (b'send_to_emergency', b'send to emergency contact'), (b'send_to_self_and_guardian', b'send to user and guardian'), (b'send_to_self_and_emergency', b'send to user and emergency contact'), (b'send_to_guardian_and_emergency', b'send to guardian and emergency contact'), (b'send_to_self_and_guardian_and_emergency', b'send to user and guardian and emergency contact')])),
                ('sender', models.TextField(null=True, blank=True)),
                ('created_at', models.DateTimeField(default=datetime.datetime.now, help_text=b'The time this object was created at. Useful for informational purposes, and also as a safety mechanism for preventing un-sent (because of previous bugs and failures), out-of-date messages from being sent.', editable=False)),
                ('processed', models.BooleanField(default=False, db_index=True)),
                ('processed_by', models.DateTimeField(default=None, null=True, db_index=True)),
                ('priority_level', models.IntegerField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='MessageVars',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('pickled_provider', models.TextField()),
                ('provider_name', models.CharField(max_length=128)),
                ('messagerequest', models.ForeignKey(to='dbmail.MessageRequest')),
            ],
            options={
                'verbose_name_plural': 'Message Variables',
            },
        ),
        migrations.CreateModel(
            name='PlainRedirect',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('original', models.CharField(max_length=512)),
                ('destination', models.CharField(max_length=512)),
            ],
            options={
                'ordering': ('original',),
            },
        ),
        migrations.CreateModel(
            name='TextOfEmail',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('send_to', models.CharField(max_length=1024)),
                ('send_from', models.CharField(max_length=1024)),
                ('subject', models.TextField()),
                ('msgtext', models.TextField()),
                ('created_at', models.DateTimeField(help_text=b'The time this object was created at. Useful for informational purposes, and also as a safety mechanism for preventing un-sent (because of previous bugs and failures), out-of-date messages from being sent.', editable=False)),
                ('sent', models.DateTimeField(null=True, blank=True)),
                ('sent_by', models.DateTimeField(default=None, null=True, db_index=True)),
                ('tries', models.IntegerField(default=0)),
            ],
            options={
                'verbose_name_plural': 'Email Texts',
            },
        ),
    ]
