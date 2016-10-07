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

RESOURCE_NAMES = [x[0] for x in RESOURCE_TYPES.values_list("name") if x[0] !=
        RTYPE_CLASS_SPACE.name]

sched_filename = os.path.expanduser(raw_input("Full path to CSV file from schedules: "))
sched_csvfile = open(sched_filename, "r")
sched_reader = csv.reader(sched_csvfile)

furnish_filename = os.path.expanduser(raw_input("Full path to CSV file with furnishings: "))
furnish_csvfile = open(furnish_filename, "r")
furnish_reader = csv.reader(furnish_csvfile)
furnish_rows = list(furnish_reader)
furnish_headers = furnish_rows[0]
furnish_classrooms = furnish_rows[0:]

RESOURCE_MATCHING = {}
def get_available_furnishings():
    return [(i, header) for i, header in enumerate(furnish_headers) if i not in
            RESOURCE_MATCHING.values()]

while True:
    print "Now attempting to match resource types..."
    for resource_name in RESOURCE_NAMES:
        if resource_name in furnish_headers:
            RESOURCE_MATCHING[resource_name] = \
                furnish_headers.index(resource_name)
        else:
            available_furnishings = get_available_furnishings()
            print "Unable to automatically match resource type {} to furnishings \
            in spreadsheet. Available furnishings ('None' if none):
                ".format(resource_name)
            for f in available_furnishings:
                print f
            idx = raw_input("Input furnishing index: ")
            if idx == "None":
                idx = None
            else:
                idx = int(idx)
            RESOURCE_MATCHING[resource_name] = idx
    print "We have the following matchings:"
    for res, idx in RESOURCE_MATCHING:
        furnish_name = furnish_headers[idx] if idx is not None else "None"
        print "{}: {} (Column {})".format(res, furnish_name, str(idx))
    conf = raw_input("Confirm correctness: y/n")
    if "y" in conf.lower():
        break
    else:
        RESOURCE_MATCHING = {}

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
    others = [row[RESOURCE_MATCHING[name]] == "Yes" for name in RESOURCE_NAMES]
    rooms_dict[room_number] = [capacity] + others

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
    for i, res in enumerate(list(RESOURCE_TYPES)):
        if res == RTYPE_CLASS_SPACE:
            continue
        else:
            if room_desc[RESOURCE_MATCHING[res.name] + 1]:
                furnishings.add(res)

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
