#!/usr/bin/env python2

# Adds lunches in an empty block for users who don't have one.  Chooses the
# lunch randomly for users with both lunch blocks free.

from script_setup import *

import random

from esp.cal.models import Event
from esp.program.models import Program, StudentRegistration, RegistrationType
from esp.program.models.class_ import ClassSection
from esp.users.models import ESPUser

program = Program.objects.get(id=115)  # Change me! (Splash 2014)
relationship = RegistrationType.objects.get(name='Enrolled')

srs = StudentRegistration.valid_objects().filter(
    section__parent_class__parent_program=program,
    relationship=relationship)

srs_pairs = srs.values_list('user', 'section')

users = ESPUser.objects.filter(id__in=srs.values_list('user'))
sections = ClassSection.objects.filter(
    parent_class__parent_program=program
).prefetch_related('meeting_times')
timeblocks = Event.objects.filter(
    program=program, event_type__description='Class Time Block')

users_by_id = {user.id: user for user in users}
sections_by_id = {section.id: section for section in sections}
timeblocks_by_id = {timeblock.id: timeblock for timeblock in timeblocks}
sections_by_user_timeblock = {
    (user_id, timeblock.id): section_id
    for user_id, section_id in srs_pairs
    for timeblock in sections_by_id[section_id].meeting_times.all()}

lunches = ClassSection.objects.filter(parent_class__parent_program=program,
                                      parent_class__category__category='Lunch',
                                      meeting_times__isnull=False
                                      ).values_list('meeting_times', 'id')
lunches_by_timeblock = dict(lunches)
lunch_ids = set(lunches_by_timeblock.values())

lunchtimes_by_day = {}
for timeblock_id, section_id in lunches:
    date = timeblocks_by_id[timeblock_id].start.date()
    if date not in lunchtimes_by_day:
        lunchtimes_by_day[date] = [timeblock_id]
    else:
        lunchtimes_by_day[date].append(timeblock_id)

for user in users:
    for day, lunchtimes in lunchtimes_by_day.iteritems():
        # If the user has any lunch already, continue to the next day/user
        if any(sections_by_user_timeblock.get((user.id, lunchtime_id), 0)
               in lunch_ids for lunchtime_id in lunchtimes):
            print "[", user.username, "already had lunch]"
            continue
        # Otherwise, check lunch blocks in a random order until finding an
        # empty one
        random.shuffle(lunchtimes)
        hungry = True
        for lunchtime_id in lunchtimes:
            if (user.id, lunchtime_id) not in sections_by_user_timeblock:
                # The user has nothing here; assign a lunch and skip to the
                # next day/user
                print "assigning", user.username, "to lunch",
                print timeblocks_by_id[lunchtime_id]
                StudentRegistration.objects.create(
                    user=users_by_id[user.id],
                    section=sections_by_id[lunches_by_timeblock[lunchtime_id]],
                    relationship=relationship)
                hungry = False
                break
        if hungry:
            print "***", user.username, "is hungry ***"
            hungry = False
