# Script for checking for scheduling inconsistencies.
# Author: Theodore Hwa <hwatheod@cs.stanford.edu>
# Usage: Change the program_name line below to your current program, then run.
#
# This script checks for the following:
# 1. Every class section has the expected duration.
# 2. Events in the Resources for the section match the Events of the meeting_times for the section.
# 3. No two class sections have the same teacher at the same time.
# 4. No two class sections are using the same Resources (usually means same room at the same time).
#
# Unscheduled classes are ignored.
#
# Step 4 takes much longer to run than the others (O(n^2) where n is the number of scheduled classes).

from esp.program.models import ClassSubject, ClassSection, Program

program_name = '2011_Spring'  # change to your program
program = Program.objects.get(anchor__name = program_name)
classes = ClassSubject.objects.filter(parent_program__anchor__name=program_name)
teachers = set()
for c in classes:
    teachers = teachers.union(c.teachers())
teachers = list(teachers)
sections = ClassSection.objects.filter(parent_class__parent_program__anchor__name=program_name)

# Every class section has the expected duration.

print "Checking: Every class section has the expected duration."
for s in sections:
    expected_duration = int(round(s.duration)) # assumes each event slot = 1hr
    actual_duration = len(s.get_meeting_times())
    if expected_duration != actual_duration and actual_duration > 0:  # >0 to avoid unscheduled classes
        print str(s.emailcode()) + ' has expected duration ' + str(expected_duration) + ', actual duration ' + str(actual_duration)

# The Events in the Resources for the section match the Events of the meeting_times for the section.
print "Checking: The Events in the Resources for the section match the Events of the meeting_times for the section."
for s in sections:
    resource_events = [x.event for x in s.getResources()]
    meeting_time_events = s.get_meeting_times()
    if sorted(resource_events) != sorted(meeting_time_events):
        print str(s.emailcode()) + ' has resource events: '
        print resource_events
        print str(s.emailcode()) + ' has meeting_time events: '
        print meeting_time_events

# No two class sections have the same teacher at the same time.
print "Checking: No two class sections have the same teacher at the same time."
for t in teachers:
    sections_taught = list(t.getTaughtSectionsFromProgram(program)) # I don't trust the QuerySet to iterate in the same order for both loops.
    for i in range(0, len(sections_taught)):
        s1 = sections_taught[i]
        c1_times = s1.get_meeting_times()
        if len(c1_times) == 0:
            continue
        for j in range(i+1, len(sections_taught)):
            s2 = sections_taught[j]
            c2_times = s2.get_meeting_times()
            if len(c2_times) > 0:
                if set(c1_times).intersection(c2_times) != set():
                    print str(s1.emailcode()) + ' and ' + str(s2.emailcode()) + ' are both taught by ' + str(t) + ' at ' + str(list(set(c1_times).intersection(c2_times)))

# No two class sections are using the same resources (i.e. same room at the same time).
print "Checking: No two class sections are using the same resources (i.e. same room at the same time)."
sectionlist = list(sections)   # I don't trust the QuerySet to iterate in the same order for both loops.
numsections = len(sectionlist)
count=0
for i in range(0,numsections):
    s1 = sectionlist[i]
    s1_used_resources = set(s1.getResources())
    if len(s1_used_resources) == 0:
        continue
    for j in range(i+1, numsections):
        s2 = sectionlist[j]
        s2_used_resources = set(s2.getResources())
        if len(s2_used_resources) > 0:
            if s1_used_resources.intersection(s2_used_resources) != set():
                print str(s1.emailcode()) + ' and ' + str(s2.emailcode()) + ' are both using: ' + str([[x.name, x.event] for x in set(s1_used_resources).intersection(s2_used_resources)])




