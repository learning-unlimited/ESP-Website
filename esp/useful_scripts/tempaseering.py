#!/usr/bin/python

from esp.program.models import ClassSection, Program
from esp.users.models import ESPUser
from datetime import datetime

p = Program.objects.all().order_by('-id')[2]

times = p.getTimeSlots()

now = datetime.now()

students = ESPUser.objects.filter(studentregistration__start_date__lte=now,
                                  studentregistration__end_date__gt=now,
                                  studentregistration__section__parent_class__parent_program=p).order_by('username').distinct()


students = list(students) ## So I can tack variables onto each student and have them stick

for s in students:
    s._missing_blocks = []
    stu_times_ids = []
    stu_times = []
    for sec in s.getEnrolledSections(program=p):
        for t in sec.get_meeting_times():
            stu_times.append(t)
            stu_times_ids.append(int(t.id))
    for t in times.exclude(id__in=stu_times_ids):
        prio_secs = s.getSections(program=p, verbs=['Priority/1']).filter(meeting_times=t).exclude(meeting_times__in=stu_times_ids)
        interest_secs = s.getSections(program=p, verbs=['Interested']).filter(meeting_times=t).exclude(meeting_times__in=stu_times_ids)

        interest_secs_count = interest_secs.count()
        if bool(prio_secs) and (interest_secs_count > 0):
            s._missing_blocks.append((t, interest_secs_count))
            print "Student not scheduled:", s.username, t, prio_secs.count(), interest_secs.count()

students_by_missed_classes = sorted([(len(s._missing_blocks), s) for s in students])
