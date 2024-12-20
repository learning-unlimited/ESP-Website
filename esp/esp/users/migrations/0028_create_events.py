# -*- coding: utf-8 -*-
# Generated by Django 1.11.29 on 2022-07-26 20:28
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations

EVENT_CHOICES=(
    ("student_survey", "Completed student survey"),
    ("teacher_survey", "Completed teacher survey"),
    ("reg_confirmed", "Confirmed registration"),
    ("attended", "Attended program"),
    ("checked_out", "Checked out of program"),
    ("conf_email", "Was sent confirmation email"),
    ("teacher_quiz_done", "Completed teacher quiz"),
    ("paid", "Paid for program"),
    ("med", "Submitted medical form"),
    ("med_bypass", "Recieved medical bypass"),
    ("liab", "Submitted liability form"),
    ("onsite", "Registered for program onsite"),
    ("schedule_printed", "Printed student schedule onsite"),
    ("teacheracknowledgement", "Did teacher acknowledgement"),
    ("studentacknowledgement", "Did student acknowledgement"),
    ("lunch_selected", "Selected a lunch block"),
    ("student_extra_form_done", "Filled out Student Custom Form"),
    ("teacher_extra_form_done", "Filled out Teacher Custom Form"),
    ("extra_costs_done", "Filled out Student Extra Costs Form"),
    ("donation_done", "Filled out Donation Form"),
    ("waitlist", "Waitlisted for a program"),
    ("interview", "Teacher-interviewed for a program"),
    ("teacher_training", "Attended teacher-training for a program"),
    ("teacher_checked_in", "Teacher checked in for teaching on the day of the program"),
    ("twophase_reg_done", "Completed two-phase registration"),
)

def create_events(apps, schema_editor):
    RecordType = apps.get_model('users', 'RecordType')
    for event in EVENT_CHOICES:
        RecordType.objects.create(name = event[0], description = event[1])

def delete_events(apps, schema_editor):
    RecordType = apps.get_model('users', 'RecordType')
    for event in EVENT_CHOICES:
        RecordType.objects.get(name = event[0], description = event[1]).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('users', '0027_auto_20220726_2027'),
    ]

    operations = [
        migrations.RunPython(create_events, delete_events),
    ]
