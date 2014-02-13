#!/usr/bin/env python2
#
# Import classrooms from a CSV file. Columns should be:
#   Start Date: 01-Mar-14 (meaning March 1st, 2014)
#   Begin Time: 700 (meaning 7:00 AM -- on the hour, not five minutes after)
#   End Time: 2000 (meaning 8:00 PM)
#   Building: 1
#   Room: 136 (meaining 1-136 when put together)
#
# Room capacities and furnishings are drawn from a reference program of your choice.
#

from script_setup import *

import csv
import os

from datetime import datetime

ETYPE_CLASSBLOCK = EventType.objects.get(description='Class Time Block')
RTYPE_CLASSROOM = ResourceType.get_or_create('Classroom')
PROGRAM = Program.objects.get(name=raw_input("Program name: "))
REFPROG = Program.objects.get(name=raw_input("Reference program: "))
filename = os.path.expanduser(raw_input("Full path to CSV file: "))
csvfile = open(filename, "r")
reader = csv.reader(csvfile)

for row in reader:
    # Parse Input
    date = datetime.strptime(row[0], "%d-%b-%y").date()
    start = datetime.combine(date, datetime.strptime(row[1], "%H%M").time())
    end = datetime.combine(date, datetime.strptime(row[2], "%H%M").time())
    room_number = "%s-%s" % (row[3], row[4])

    # Find Reference Room from Reference Program
    results = Resource.objects.filter(event__program=REFPROG,
                                      res_type=RTYPE_CLASSROOM,
                                      name=room_number)
    if not results:
        print "Couldn't find reference information for %s; skipping" % room_number
        continue
    reference = results[0]

    timeblocks = Event.objects.filter(start__gte=start, end__lte=end,
                                      event_type=ETYPE_CLASSBLOCK,
                                      program=PROGRAM)

    # Create Clasrooms with Furnishings
    for block in timeblocks:
        room = Resource()
        room.num_students = reference.num_students
        room.event = block
        room.res_type = RTYPE_CLASSROOM
        room.name = room_number
        room.save()

        original_resources = Resource.objects.filter(group_id=reference.group_id)
        for original_resource in original_resources:
            if original_resource.res_type == RTYPE_CLASSROOM:
                continue
            
            resource = Resource()
            resource.event = block
            resource.res_type = original_resource.res_type
            resource.name = original_resource.res_type.name + ' for ' + room_number
            resource.group_id = room.group_id
            resource.save()

print "Done!"
