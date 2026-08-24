from __future__ import print_function
from script_setup import *
import sys

if len(sys.argv) < 2:
    print("Usage: {} <program ID>".format(sys.argv[0]))
    print("You can get program IDs from an admin page, probably /admin/program/program/", file=sys.stderr)
    exit(1)

contr = ClassChangeController(program=Program.objects.get(id=int(sys.argv[1])), stats_display=True)
print("Note: I don't know what any of these stats actually mean:")
print("Students not checked in:", len(contr.students_not_checked_in))
print("Attended students:", len(contr.program.students()['attended']))
print("Students in controller:", len(contr.students))
print("Intersection of students in controller and attended:", len(set(contr.students.values_list('id', flat=True)) & set(contr.program.students()['attended'].values_list('id', flat=True))))
contr.compute_assignments()
# contr.save_assignments()
# contr.send_emails()
# import pickle
# pickle.dump(contr, open('/root/contr.pkl', 'wb'))
