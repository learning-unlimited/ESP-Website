#!/usr/bin/env python2
#
# Import classrooms from a CSV file. Columns should be:
#   Date: 11/22/2014
#   Begin Time: noon
#   End Time: 10:00p
#   Classroom: 1-115
#
# Room capacities and furnishings are drawn from a reference program of your
# choice. Note that the 'Sound system' resource should now be called 'Speakers'.
#

from script_setup import *

import csv
import os

from datetime import datetime

ETYPE_CLASSBLOCK = EventType.objects.get(description='Class Time Block')
RTYPE_CLASSROOM = ResourceType.get_or_create('Classroom')

PROGRAM = Program.objects.get(name=raw_input("Program name: "))
REFPROG = Program.objects.get(name=raw_input("Reference program: "))

RESOURCE_TYPES = ResourceType.objects.filter(program=PROGRAM)
RTYPE_CLASS_SPACE = RESOURCE_TYPES.get(name__iexact='Classroom space')

filename = os.path.expanduser(raw_input("Full path to CSV file: "))
csvfile = open(filename, "r")
reader = csv.reader(csvfile)

def parse_time(date, time):
    if time == "noon":
        time = "12:00p"
    elif time == "midnight":
        time = "11:00p"
    time = (time + "m").upper()
    return datetime.combine(date, datetime.strptime(time, "%I:%M%p").time())

for row in reader:
    # Parse Input
    date = datetime.strptime(row[0], "%m/%d/%Y").date()
    start = parse_time(date, row[1])
    end = parse_time(date, row[2])
    room_number = row[3]

    # Test parsing code
    print "%s from %s to %s" % (room_number, start.__repr__(), end.__repr__())

    # Find Reference Room from Reference Program
    results = Resource.objects.filter(res_type=RTYPE_CLASSROOM,
                                      name=room_number).order_by("-id")
    if not results:
        print "Couldn't find reference information for %s; skipping" % room_number
        continue
    reference = results[0]

    timeblocks = Event.objects.filter(start__gte=start, end__lte=end,
                                      event_type=ETYPE_CLASSBLOCK,
                                      program=PROGRAM)

    # Because most ResourceTypes are tied to a specific program, convert from
    # last year's ResourceTypes to this year's by comparing the names. Nasty
    # caveat: 'Sound system' is now called 'Speakers'.
    furnishings = set() # a set of ResourceTypes, not Resources
    furnishings.add(RTYPE_CLASS_SPACE) # always add classroom space

    ref_furnishings = Resource.objects.filter(res_group=reference.res_group)
    for f in ref_furnishings:
        if f.res_type == RTYPE_CLASSROOM:
            # skip the classroom resource itself; we only want to copy projectors
            # and movable tables and stuff
            continue

        search_term = f.res_type.name
        if 'sound system' in search_term.lower():
            search_term = 'Speakers'
        results = ResourceType.objects.filter(program=PROGRAM,
                                              name__iexact=search_term)
        if len(results) == 0:
            print "Could not add %s resource for %s" \
                % (search_term, room_number)
            continue
        if len(results) > 1:
            print "Multiple results for %s resource for %s; skipping" \
                % (search_term, room_number)
            continue
        furnishings.add(results[0])

    # Create Clasrooms with Furnishings
    for block in timeblocks:
        room = Resource()
        room.num_students = reference.num_students
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
