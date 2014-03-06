#!/usr/bin/env python2
# Write student emergency contact information (name, email address and, if
# applicable, cell number) to a CSV file.

from script_setup import *

import csv
import re

prog = Program.objects.get(url=raw_input("Program URL (e.g. Spark/2014): "))
rawstudents = open(os.path.expanduser(raw_input("Output Students To: ")), "wb")
rawteachers = open(os.path.expanduser(raw_input("Output Teachers To: ")), "wb")
csvstudents = csv.writer(rawstudents, dialect="excel")
csvteachers = csv.writer(rawteachers, dialect="excel")

students = prog.students()["enrolled"]
teachers = prog.teachers()["class_approved"]

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
        print "Processed %d of %d Students" % (count, students.count())

    if student.isAdmin():
        print "Skipping admin %s" % student.name()
        continue

    process_user(csvstudents, student)
    count += 1

count = 1
for teacher in teachers:
    if count % 10 == 0:
        print "Processed %d of %d Teachers" % (count, teachers.count())

    process_user(csvteachers, teacher)
    count += 1

rawstudents.close()
rawteachers.close()
print "Done!"
