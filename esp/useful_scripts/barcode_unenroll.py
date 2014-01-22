# Kick students out of the next hour's classes if they haven't
# checked in yet.

# Usage:
# # update PROG_ID, below
# from barcode_unenroll import *
# # review 'registrations'
# doit()

PROG_ID = 101

from script_setup import *

from esp.program.models import Program, StudentRegistration, ClassSection
from esp.users.models import ESPUser
from esp.users.models.userbits import UserBit
from esp.datatree.models import GetNode
from datetime import datetime, timedelta
from django.db.models.aggregates import Min

prog = Program.objects.get(id=PROG_ID)
# classes that started more than 60 minutes ago
passed_sections = prog.sections().annotate(begin_time=Min("meeting_times__start")).filter(status=10, parent_class__status=10, begin_time__start__lt=datetime.now() - timedelta(minutes=60))
# students who are enrolled in a class that started more than 60 minutes ago, who have not checked in
students = ESPUser.objects.filter(studentregistration__in=StudentRegistration.valid_objects(), studentregistration__relationship=1, studentregistration__section__in=passed_sections).distinct().exclude(record__program=prog, record__event='attended')
# classes that start in the next 60 minutes
upcoming_sections = prog.sections().annotate(begin_time=Min("meeting_times__start")).filter(status=10, parent_class__status=10, begin_time__start__gt=datetime.now(), begin_time__start__lt=datetime.now() + timedelta(minutes=60))
# registrations of missing students for upcoming classes
registrations = StudentRegistration.valid_objects().filter(user__in=students, section__in=upcoming_sections, relationship=1)
print "Candidate Registrations to Delete:", len(registrations)
print registrations
print "Run doit() to kick students out."

def doit():
    global registrations
    registrations.update(end_date=datetime.now())
    print 'Expired:', registrations
