#!/usr/bin/env python2
#
# Import classrooms from two csv files: one from schedules, and one we make with furnishings.
# From schedules, columns should be:
#   Date: 11/22/2014
#   Begin Time: noon
#   End Time: 10:00p
#   Classroom: 1-115
#
# Resource types are specific to Spark 2015. If you are trying to use this script on
# a different program, check them.
#

from script_setup import *

import csv
import os

from datetime import datetime

ETYPE_CLASSBLOCK = EventType.objects.get(description='Class Time Block')
RTYPE_CLASSROOM = ResourceType.get_or_create('Classroom')

#PROGRAM = Program.objects.get(name=raw_input("Program name: "))
PROGRAM = Program.objects.get(id=124)

RESOURCE_TYPES = ResourceType.objects.filter(program=PROGRAM)
RTYPE_CLASS_SPACE = RESOURCE_TYPES.get(name__iexact='Classroom space')

PROJECTOR = RESOURCE_TYPES.get(name__icontains="projector")
SPEAKERS = RESOURCE_TYPES.get(name__icontains="speaker")
MOVEABLE = RESOURCE_TYPES.get(name__icontains="moveable")
TABLES = RESOURCE_TYPES.get(name__icontains="large")
BOARDS = RESOURCE_TYPES.get(name__icontains="board")

#sched_filename = os.path.expanduser(raw_input("Full path to CSV file from prescheduling: "))
sched_filename = os.path.expanduser("/home/mgersh/prescheduling.csv")
sched_csvfile = open(sched_filename, "r")
sched_reader = csv.reader(sched_csvfile)

rooms_dict = {}


for row in sched_reader:
    # Parse Input
    section = ClassSection.objects.get(id=int(row[0]))
    start_event = Event.objects.get(id=int(row[2]))
    room = Resource.objects.get(name=row[1], event=start_event).name

    current_start = section.start_time()
    if current_start:
        try:
            current_room = section.resourceassignment_set.get(resource__event=current_start, resource__res_type__name="Classroom").resource.name
        except:
            print("error on", section)
            current_room = None
    else:
        current_room = None
    if start_event != current_start:
        print(section, start_event, room, current_start, current_room)
    elif current_room != room:
        print(section, room, current_room)

#    print section, room, start_event
