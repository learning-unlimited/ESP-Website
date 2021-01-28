#!/usr/bin/env python2
"""Script to dump zip code data to CSV.

Writes a CSV with a column for each of various sets of students, and a row for
each zip code, with the number of students from that zip code at that program
in the cell.
"""

from script_setup import *

import collections
import csv
import os

from django.conf import settings

from esp.users.models import ESPUser
from esp.program.models import ProgramModule
from esp.utils.query_utils import nest_Q

filename = os.path.join(settings.PROJECT_ROOT, 'zip_data.csv')

student_sets = [
    ('All users', ESPUser.objects.all()),
    ('Signed up for a class', ESPUser.objects.filter(
        nest_Q(StudentRegistration.is_valid_qobject(), 'studentregistration'),
        studentregistration__isnull=False)),
]

for program in Program.objects.all():
    try:
        s = program.students()
    except ProgramModule.CannotGetClassException:
        # If there are modules that don't exist (either because they're too
        # old, or on a dev server because they're too new for your version of
        # the code), just skip the program.  Depending whether things are
        # cached, this could be one of two different errors.
        continue
    except ImportError:
        continue
    if 'attended' in s:
        attended = s['attended']
        if attended:
            student_sets.append(('Attended %s' % program.name, attended))
    if 'enrolled' in s:
        enrolled = s['enrolled']
        if enrolled:
            student_sets.append(('Enrolled in %s' % program.name, enrolled))

# Because getting the right zipcode is hard, just build them into a dict per
# user, and then we can use that instead of trying to get them in each query.
user_zipcodes = {}
all_users_query = ESPUser.objects.filter(contactinfo__as_user__isnull=False).select_related(
    'contactinfo_set', 'contactinfo_set__address_zip'
).values_list('id', 'contactinfo__address_zip').distinct('contactinfo').order_by('contactinfo')
for user, zipcode in all_users_query:
    user_zipcodes[user] = zipcode

zip_data = []
for set_name, user_set in student_sets:
    zipcode_freqs = collections.defaultdict(int)
    for user_id in user_set.values_list('id', flat=True).distinct():
        if user_id in user_zipcodes:
            zipcode_freqs[user_zipcodes[user_id]] += 1
    zip_data.append((set_name, zipcode_freqs))

all_zipcodes = list(set(user_zipcodes.values()))
all_zipcodes.sort()
# CSV has format:
#     , name1, name2, ...
# zip1, num11, num12, ...
# zip2, num21, num22, ...
# ...
first_row = [""] + [set_name for set_name, _ in zip_data]
zip_rows = [[zipcode] + [zipcode_freqs[zipcode]
                         for _, zipcode_freqs in zip_data]
            for zipcode in all_zipcodes]

with open(filename, 'w') as f:
    w = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
    w.writerows([first_row] + zip_rows)
