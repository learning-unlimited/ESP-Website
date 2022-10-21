# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2022-07-26 20:28
from __future__ import unicode_literals

from django.db import migrations

def link_event(apps, schema_editor):
    Record = apps.get_model('users', 'Record')
    RecordType = apps.get_model('users', 'RecordType')
    for rec in Record.objects.all():
        if rec.event not in [None, ""]:
            if rec.event == "medical":
                rec.event = "med"
                rec.save()
            if rec.event == "liability":
                rec.event = "liab"
                rec.save()
            event = RecordType.objects.get(name=rec.event)
            rec.event_link = event
            rec.save()

def unlink_event(apps, schema_editor):
    Record = apps.get_model('users', 'Record')
    RecordType = apps.get_model('users', 'RecordType')
    for rec in Record.objects.all():
        if rec.event_link is not None:
            rec.event = rec.event_link.name
            rec.save()

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0028_create_events'),
    ]

    operations = [
        migrations.RunPython(link_event, unlink_event),
    ]
