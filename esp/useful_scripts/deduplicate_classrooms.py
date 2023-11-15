#!/usr/bin/env python
#
# Check a program for duplicate identical classroom Resources (same name
# and time).
#

from __future__ import absolute_import
from __future__ import print_function
from script_setup import *
from six.moves import input

ETYPE_CLASSBLOCK = EventType.objects.get(description='Class Time Block')
RTYPE_CLASSROOM = ResourceType.get_or_create('Classroom')

PROGRAM = Program.objects.get(name=input("Program name: "))

classrooms = Resource.objects.filter(res_type=RTYPE_CLASSROOM,
                                     event__program=PROGRAM)
history = set()

for classroom in classrooms:
    tag = (classroom.name, classroom.event.__str__())
    if tag in history:
        print("Warning! Duplicate: %s during %s" % tag)
    else:
        history.add(tag)
