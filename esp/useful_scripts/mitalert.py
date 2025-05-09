#!/usr/bin/env python
# Write student emergency contact information (name, email address and, if
# known, cell number) to a CSV file.

from __future__ import absolute_import
from __future__ import print_function
from script_setup import *

import csv
import re
import sys
from io import open
from six.moves import input

prog = Program.objects.get(url=input("Program URL (e.g. Spark/2014): "))
rawfile = open(os.path.expanduser(input("Output CSV: ")), "wb")
csvfile = csv.writer(rawfile, dialect="excel")

students = prog.students()["enrolled"]

def process_user(csv, user):
    cell = user.getLastProfile().contact_user.phone_cell
    if cell and not re.match(r"\d{3}-\d{3}-\d{4}", cell):
        raise ValueError("Cell for %s not formatted properly!" % user.name())
    csv.writerow([
            user.name(),
            user.email,
            cell])

count = 1
for student in students:
    if count % 10 == 0:
        sys.stdout.write("\rProcessed %d of %d Students" % (count, students.count()))
        sys.stdout.flush()

    if student.isAdmin():
        print(("\rSkipping admin %s" + " " * 20) % student.name())
        continue

    process_user(csvfile, student)
    count += 1

rawfile.close()
print("\rDone!", " " * 30)
