#!/usr/bin/env python
"""
Kick students out of their classes in the next two hours if they haven't checked in yet.
This has been heavily modified from the original to reflect the Stanford Splash policy.
"""

import argparse

from script_setup import *

from esp.program.models import Program, StudentRegistration
from esp.users.models import ESPUser
from datetime import datetime, timedelta
from django.db.models.aggregates import Min

parser = argparse.ArgumentParser(description='Unenroll missing students from classes.')
parser.add_argument('program_id', type=int, help='ID of the current program')
# parser.add_argument('--per-hour', dest='per_hour', action='store_true', help='Include this argument to clear registrations only for classes starting in the next 60 minutes.')

args = parser.parse_args()

prog = Program.objects.get(id=args.program_id)
# classes that started more than 60 minutes ago
#passed_sections = prog.sections().annotate(begin_time=Min("meeting_times__start")).filter(status=10, parent_class__status=10, begin_time__start__lt=datetime.now() - timedelta(minutes=60))
# students who are enrolled in a class that started more than 60 minutes ago, who have not checked in


# students who are enrolled in at least one class, who have not checked in
# You'd think you could just do it this way in one line, but it doesn't work for some reason I have not figured out.
# students = ESPUser.objects.filter(studentregistration__in=StudentRegistration.valid_objects(), studentregistration__relationship__name='Enrolled', studentregistration__section__in=passed_sections).distinct().exclude(record__program=prog, record__event='attended')
all_students = ESPUser.objects.filter(studentregistration__in=StudentRegistration.valid_objects(), studentregistration__relationship__name='Enrolled', studentregistration__section__parent_class__parent_program=prog).distinct()
students_checked_in = Record.objects.filter(program=prog, event='attended').values_list('user',flat=True).distinct()
students = all_students.exclude(id__in=students_checked_in)

# classes that start in the next 120 minutes
upcoming_sections = prog.sections().annotate(begin_time=Min("meeting_times__start")).filter(status=10, parent_class__status=10, parent_class__parent_program=prog, begin_time__start__lt=datetime.now() + timedelta(minutes=120))
    
# registrations of missing students for upcoming classes
registrations = StudentRegistration.valid_objects().filter(user__in=students, section__in=upcoming_sections, relationship__name='Enrolled')
print "Candidate Registrations to Delete:", len(registrations)
print registrations
cmd_str = raw_input("Would you like to delete these registrations [y/N]? --> ")
if cmd_str.strip().lower() == 'y':
    registrations.update(end_date=datetime.now())
    print 'Expired:', registrations
else:
    print 'Action cancelled.'
