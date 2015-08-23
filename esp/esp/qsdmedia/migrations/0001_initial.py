# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
    ]

    operations = [
        migrations.CreateModel(
            name='Media',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('friendly_name', models.TextField()),
                ('target_file', models.FileField(upload_to=b'uploaded')),
                ('size', models.IntegerField(null=True, editable=False, blank=True)),
                ('format', models.TextField(null=True, blank=True)),
                ('mime_type', models.CharField(max_length=256, null=True, editable=False, blank=True)),
                ('file_extension', models.TextField(max_length=16, null=True, editable=False, blank=True)),
                ('file_name', models.TextField(max_length=256, null=True, editable=False, blank=True)),
                ('hashed_name', models.TextField(max_length=256, null=True, editable=False, blank=True)),
                ('owner_id', models.PositiveIntegerField(null=True, blank=True)),
                ('owner_type', models.ForeignKey(blank=True, to='contenttypes.ContentType', null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Paper',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_mutable_text', models.BooleanField(default=False)),
                ('media', models.ForeignKey(to='qsdmedia.Media', unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='PaperType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type_description', models.TextField(null=True, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Picture',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_arbitrarily_resizable_format', models.BooleanField(default=False)),
                ('x_resolution', models.IntegerField(null=True, blank=True)),
                ('y_resolution', models.IntegerField(null=True, blank=True)),
                ('media', models.ForeignKey(to='qsdmedia.Media', unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Video',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('container_format', models.TextField(null=True, blank=True)),
                ('audio_codec', models.TextField(null=True, blank=True)),
                ('video_codec', models.TextField(null=True, blank=True)),
                ('bitrate', models.IntegerField(null=True, blank=True)),
                ('duration', models.IntegerField(null=True, blank=True)),
                ('media', models.ForeignKey(to='qsdmedia.Media', unique=True)),
            ],
        ),
        migrations.AddField(
            model_name='paper',
            name='type',
            field=models.ForeignKey(to='qsdmedia.PaperType'),
        ),
    ]
