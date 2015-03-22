#!/usr/bin/env python2
#
# Check a program for duplicate identical classroom Resources (same name
# and time).
#

from script_setup import *

ETYPE_CLASSBLOCK = EventType.objects.get(description='Class Time Block')
RTYPE_CLASSROOM = ResourceType.get_or_create('Classroom')

PROGRAM = Program.objects.get(name=raw_input("Program name: "))

classrooms = Resource.objects.filter(res_type=RTYPE_CLASSROOM,
                                     event__program=PROGRAM)
history = set()

for classroom in classrooms:
    tag = (classroom.name, classroom.event.__str__())
    if tag in history:
        print "Warning! Duplicate: %s during %s" % tag
    else:
        history.add(tag)
