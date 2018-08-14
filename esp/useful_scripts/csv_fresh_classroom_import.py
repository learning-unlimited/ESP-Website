#!/usr/bin/env python2
#
# Import classrooms from two csv files: one from schedules, and one we make
# with furnishings.
# From schedules, columns should be:
#   Date: 11/22/2014
#   Begin Time: noon
#   End Time: 10:00p
#   Classroom: 1-115
#

from script_setup import EventType, ResourceType, Program, Event, Resource

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
RESOURCE_NAMES = [x[0] for x in RESOURCE_TYPES.values_list("name")]

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
FURNISH_CAPACITY_COL = 1

rooms_dict = {}


def subsequence_match(item, options, exclude):
    item = item.lower()
    if item == "":
        return None
    # http://stackoverflow.com/questions/3673434/find-subsequences-of-strings-within-strings
    pattern = ".*".join(item)
    matches = []
    for i, option in enumerate(options):
        if re.search(pattern, option.lower()):
            matches.append(i)
    if len(matches) == 1:
        return matches[0]
    else:
        return None


def do_match(items_to_match, possible_options, description,
             force_unique=False):
    print "Now attempting to match {}s...".format(description)
    matching_idx = {}
    force_manual = False
    while True:
        for item in items_to_match:
            # We match subsequences in order to match as loosely as
            # possible. Since the user is supposed to verify anyway,
            # this shouldn't cause any major issues.
            match_attempt = subsequence_match(
                    item, possible_options, matching_idx.values())
            if match_attempt is None or force_manual:
                if force_manual:
                    print "Manual mode forced due to attempt failure."
                print (
                    "Unable to automatically match {desc} "
                    "'{}' to possible {desc}s."
                ).format(item, desc=description)
                print ""
                print "Available {}s:".format(description)
                allowed = set()
                for i, option in enumerate(possible_options):
                    if force_unique and i in matching_idx.values():
                        continue
                    else:
                        allowed.add(i)
                        print i, option

                valid = False
                while not valid:
                    input_idx = raw_input(
                        "Input {desc} index for '{}' (or 'None'): ".format(
                            item, desc=description))
                    if input_idx == "None":
                        match_attempt = None
                        valid = True
                    else:
                        try:
                            match_attempt = int(input_idx)
                            assert match_attempt in allowed, "Invalid index"
                            valid = True
                        except:
                            print "Invalid choice: {}; try again.".format(
                                    input_idx)
            matching_idx[item] = match_attempt
        print "We have the following matchings:"
        print matching_idx
        for item, match_idx in matching_idx.iteritems():
            match_name = None if match_idx is None else \
                possible_options[match_idx]
            print "{}: {} ({})".format(item, match_name, match_idx)
        conf = raw_input("Confirm correctness: y/n")
        if "y" in conf.lower():
            return matching_idx
        else:
            matching_idx = {}
            force_manual = True


resource_matching = do_match(RESOURCE_NAMES, furnish_headers, "resource type",
                             force_unique=True)

resource_value_matching = {}
for rtype in RESOURCE_TYPES:
    possible_values = rtype.attributes_pickled.split("|")
    if len(possible_values) == 1:
        resource_value_matching[rtype.name] = None
    else:
        rtype_idx = resource_matching[rtype.name]
        if rtype_idx is None:
            resource_value_matching[rtype.name] = None
        else:
            known_values = set(
                [row[rtype_idx] for row in furnish_classrooms
                 if row[FURNISH_ROOM_NUMBER_COL] in ALL_USED_ROOMS])
            resource_value_matching[rtype.name] = {
                    known: (possible_values[idx] if idx is not None else "")
                    for known, idx in
                    do_match(
                        known_values, possible_values, rtype.name).iteritems()}


def parse_time(date, time):
    if time == "noon":
        time = "12:00p"
    elif time == "midnight":
        time = "11:00p"
    time = (time + "m").upper()
    return datetime.combine(date, datetime.strptime(time, "%I:%M%p").time())


EXTRA_DATA = 1  # Number of extra data entries in rooms_dict
print "Reading from furnishings csv..."
for row in furnish_classrooms:
    room_number = row[FURNISH_ROOM_NUMBER_COL]
    if room_number not in ALL_USED_ROOMS:
        continue
    try:
        capacity = int(row[FURNISH_CAPACITY_COL])
        others = [
            False if resource_matching[name] is None else
            row[resource_matching[name]] == "Yes" if
            resource_value_matching[name] is None else
            resource_value_matching[name][row[resource_matching[name]]]
            for name in RESOURCE_NAMES]
        rooms_dict[room_number] = [capacity] + others
        assert len(rooms_dict[room_number]) == EXTRA_DATA + len(others), \
            "value of EXTRA_DATA is incorrect"
    except:
        print "Error reading furnishings for room {}; skipping".format(
            room_number)

skipped_rooms = set()
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

    furnishings = []  # a list of ResourceTypes and values, not Resources

    if room_number not in rooms_dict:
        skipped_rooms.add(room_number)
        print "WARNING: {} not found; skipping".format(room_number)
        continue
    room_desc = rooms_dict[room_number]
    for i, res in enumerate(list(RESOURCE_TYPES)):
        idx = RESOURCE_NAMES.index(res.name)
        if idx is not None and room_desc[idx + EXTRA_DATA]:
            furnishings.append((res, room_desc[idx + EXTRA_DATA]))

    # Create Clasrooms with Furnishings
    for block in timeblocks:
        room = Resource()
        room.num_students = room_desc[0]
        room.event = block
        room.res_type = RTYPE_CLASSROOM
        room.name = room_number
        room.save()

        for res_type, val in furnishings:
            resource = Resource()
            resource.event = block
            resource.res_type = res_type
            resource.name = res_type.name + ' for ' + room_number
            resource.res_group = room.res_group
            if val is not True:
                resource.attribute_value = val
            resource.save()

print "Done creating resources."
for r in skipped_rooms:
    print "Skipped: {}".format(r)

print "Done!"
