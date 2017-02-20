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
import re
import argparse

from datetime import datetime


ETYPE_CLASSBLOCK = EventType.objects.get(description='Class Time Block')
RTYPE_CLASSROOM = ResourceType.get_or_create('Classroom')

parser = argparse.ArgumentParser()
parser.add_argument("program", help="Program name")
parser.add_argument("sched_filename",
        help="Full path to CSV file from schedules")
parser.add_argument("furnish_filename",
        help="Full path to CSV file with furnishings")
args = parser.parse_args()

PROGRAM = Program.objects.get(name=args.program)

RESOURCE_TYPES = ResourceType.objects.filter(program=PROGRAM)
RTYPE_CLASS_SPACE = RESOURCE_TYPES.get(name__iexact='Classroom space')
POSSIBLE_SPACE_TYPES = RTYPE_CLASS_SPACE.attributes_pickled.split("|")

RESOURCE_NAMES = [x[0] for x in RESOURCE_TYPES.values_list("name") if x[0] !=
        RTYPE_CLASS_SPACE.name]

sched_filename = os.path.expanduser(args.sched_filename)
sched_csvfile = open(sched_filename, "r")
sched_reader = csv.reader(sched_csvfile)
sched_rows = list(sched_reader)
SCHED_ROOM_NUMBER_COL = 3
ALL_USED_ROOMS = set([row[SCHED_ROOM_NUMBER_COL] for row in sched_rows])

furnish_filename = os.path.expanduser(args.furnish_filename)
furnish_csvfile = open(furnish_filename, "r")
furnish_reader = csv.reader(furnish_csvfile)
furnish_rows = list(furnish_reader)
furnish_headers = furnish_rows[0]
furnish_classrooms = furnish_rows[1:]
FURNISH_ROOM_NUMBER_COL = 0

RESOURCE_MATCHING = {}
rooms_dict = {}
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
            print ("Unable to automatically match resource type {} to furnishings "
                    "in spreadsheet. Available furnishings ('None' if none): ").format(resource_name)
            for f in available_furnishings:
                print f
            idx = raw_input("Input furnishing index (or 'None'): ")
            if idx == "None":
                idx = None
            else:
                idx = int(idx)
            RESOURCE_MATCHING[resource_name] = idx
    print "We have the following matchings:"
    for res, idx in RESOURCE_MATCHING.iteritems():
        furnish_name = furnish_headers[idx] if idx is not None else "None"
        print "{}: {} (Column {})".format(res, furnish_name, str(idx))
    conf = raw_input("Confirm correctness: y/n ")
    if "y" in conf.lower():
        break
    else:
        RESOURCE_MATCHING = {}

SPACE_TYPE_MATCHING = {}
def match_space_type(space_type):
    if space_type == "":
        return ""
    # http://stackoverflow.com/questions/3673434/find-subsequences-of-strings-within-strings
    pattern = ".*".join(space_type)
    matches = []
    for possible_type in POSSIBLE_SPACE_TYPES:
        if re.search(pattern, possible_type):
            matches.append(possible_type)
    if len(matches) == 1:
        return matches[0]
    else:
        return None

def get_possible_space_Types():
    return [(i, space) for i, space in enumerate(POSSIBLE_SPACE_TYPES) if i not in
            SPACE_TYPE_MATCHING.values()]

force_manual = False
SPACE_TYPE_IDX = None
while True:
    print "Now attempting to match space type header..."
    space_header_candidates = ["space type", "classroom space"]
    for i, header in enumerate(furnish_headers):
        if header.lower() in space_header_candidates:
            SPACE_TYPE_IDX = i
            break
    if SPACE_TYPE_IDX is None or force_manual:
        print "Unable to automatically determine space type header."
        print "Available columns:"
        for f in get_available_furnishings():
            print f
        idx = raw_input("Input furnishing index (or 'None'): ")
        if idx == "None":
            SPACE_TYPE_IDX = None
        else:
            SPACE_TYPE_IDX = int(idx)
    print "Header for the classroom space type data is {}".format(
        furnish_headers[SPACE_TYPE_IDX])
    conf = raw_input("Confirm correctness: y/n ")
    if "y" in conf.lower():
        break
    else:
        SPACE_TYPE_IDX = None
        force_manual = True

force_manual = False
if SPACE_TYPE_IDX is not None:
    space_types = set([row[SPACE_TYPE_IDX] for row in furnish_classrooms
                      if row[FURNISH_ROOM_NUMBER_COL] in ALL_USED_ROOMS])
    while True:
        print "Now attempting to match space types..."
        for space_type in space_types:
            match_attempt = match_space_type(space_type)
            if match_attempt is None or force_manual:
                possible_types = get_possible_space_Types()
                if force_manual:
                    print "Manual mode forced due to attempt failure."
                print ("Unable to automatically match space type "
                "{} to possible space types.").format(space_type)
                print "Available space types:"
                for space in possible_types:
                    print space
                match_attempt = raw_input(
                    "Input space type index (or 'None'): ")
                if match_attempt == "None":
                    match_attempt = ""
                else:
                    match_attempt = POSSIBLE_SPACE_TYPES[
                        int(match_attempt)]
            SPACE_TYPE_MATCHING[space_type] = match_attempt
        print "We have the following matchings:"
        for space, possible in SPACE_TYPE_MATCHING.iteritems():
            print "{}: {}".format(space, possible)
        conf = raw_input("Confirm correctness: y/n")
        if "y" in conf.lower():
            break
        else:
            SPACE_TYPE_MATCHING = {}
            force_manual = True

def parse_time(date, time):
    if time == "noon":
        time = "12:00p"
    elif time == "midnight":
        time = "11:00p"
    time = (time + "m").upper()
    return datetime.combine(date, datetime.strptime(time, "%I:%M%p").time())

OFFSET = 2
print "Reading from furnishings csv..."
for row in furnish_classrooms:
    room_number = row[FURNISH_ROOM_NUMBER_COL]
    if room_number not in ALL_USED_ROOMS:
        continue
    try:
        capacity = int(row[1])
        space_type = SPACE_TYPE_MATCHING[row[SPACE_TYPE_IDX]] \
            if SPACE_TYPE_IDX is not None else ""
        others = [(row[RESOURCE_MATCHING[name]] == "Yes") if RESOURCE_MATCHING[name]
                is not None else False for name in RESOURCE_NAMES]
        rooms_dict[room_number] = [capacity] + [space_type] + others
    except:
        print "Error reading furnishings for room {}; skipping".format(room_number)

for row in sched_rows:
    if row[0] == "Date":
        continue
    # Parse Input
    date = datetime.strptime(row[0], "%m/%d/%Y").date()
    start = parse_time(date, row[1])
    end = parse_time(date, row[2])
    room_number = row[SCHED_ROOM_NUMBER_COL]

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

    if room_number not in rooms_dict:
        print "WARNING: {} not found; skipping".format(room_number)
        continue
    room_desc = rooms_dict[room_number]
    for i, res in enumerate(list(RESOURCE_TYPES)):
        if res == RTYPE_CLASS_SPACE:
            continue
        else:
            idx = RESOURCE_NAMES.index(res.name)
            if idx is not None and room_desc[idx + OFFSET]:
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
            if res_type == RTYPE_CLASS_SPACE:
                resource.attribute_value = room_desc[1]
            resource.save()

print "Done!"
