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

PROGRAM = Program.objects.get(name=raw_input("Program name: "))

RESOURCE_TYPES = ResourceType.objects.filter(program=PROGRAM)
RTYPE_CLASS_SPACE = RESOURCE_TYPES.get(name__iexact='Classroom space')

PROJECTOR = RESOURCE_TYPES.get(name__icontains="projector")
SPEAKERS = RESOURCE_TYPES.get(name__icontains="speaker")
MOVEABLE = RESOURCE_TYPES.get(name__icontains="moveable")
TABLES = RESOURCE_TYPES.get(name__icontains="table")
BOARDS = RESOURCE_TYPES.get(name__icontains="board")

sched_filename = os.path.expanduser(raw_input("Full path to CSV file from schedules: "))
sched_csvfile = open(sched_filename, "r")
sched_reader = csv.reader(sched_csvfile)

furnish_filename = os.path.expanduser(raw_input("Full path to CSV file with furnishings: "))
furnish_csvfile = open(furnish_filename, "r")
furnish_reader = csv.reader(furnish_filename)

rooms_dict = {}

def parse_time(date, time):
    if time == "noon":
        time = "12:00p"
    elif time == "midnight":
        time = "11:00p"
    time = (time + "m").upper()
    return datetime.combine(date, datetime.strptime(time, "%I:%M%p").time())

for row in furnish_reader:
    room_number = row[0]
    capacity = int(row[1])
    projector = (row[3] == "Yes")
    speakers = (row[4] == "Yes")
    moveable = (row[5] == "Yes")
    tables = (row[6] == "Yes")
    boards = (row[7] == "Yes")
    rooms_dict[room_number] = (capacity, projector, speakers, moveable, tables, boards)

for row in sched_reader:
    # Parse Input
    date = datetime.strptime(row[0], "%m/%d/%Y").date()
    start = parse_time(date, row[1])
    end = parse_time(date, row[2])
    room_number = row[3]

    # Test parsing code
    print "%s from %s to %s" % (room_number, start.__repr__(), end.__repr__())

    timeblocks = Event.objects.filter(start__gte=start, end__lte=end,
                                      event_type=ETYPE_CLASSBLOCK,
                                      program=PROGRAM)

    # Because most ResourceTypes are tied to a specific program, convert from
    # last year's ResourceTypes to this year's by comparing the names. Nasty
    # caveat: 'Sound system' is now called 'Speakers'.
    furnishings = set() # a set of ResourceTypes, not Resources
    furnishings.add(RTYPE_CLASS_SPACE) # always add classroom space

    room_desc = rooms_dict[room_number]
    if room_desc[1]:
        furnishings.add(PROJECTOR)
    if room_desc[2]:
        furnishings.add(SPEAKERS)
    if room_desc[3]:
        furnishings.add(MOVEABLE)
    if room_desc[4]:
        furnishings.add(TABLES)
    if room_desc[5]:
        furnishings.add(BOARDS)

    # Create Clasrooms with Furnishings
    for block in timeblocks:
        room = Resource()
        room.num_students = room_desc[0]
        room.event = block
        room.res_type = RTYPE_CLASSROOM
        room.name = room_number
        room.save()

        for res_type in furnishings:
            resource = Resource()
            resource.event = block
            resource.res_type = res_type
            resource.name = res_type.name + ' for ' + room_number
            resource.res_group = room.res_group
            resource.save()

print "Done!"
