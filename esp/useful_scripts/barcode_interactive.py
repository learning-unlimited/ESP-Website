#
# Check in Students by Barcode live
#
# Performs rapid check-in on student IDs entered via the shell. Sets
# Attendance bit only. Make sure to update the configuration below.
#
# This script should be run from the manage.py shell
#

from esp.datatree.models import *
from esp.users.models    import ESPUser, UserBit, User
from esp.program.models import Program
import sys


# CONFIGURATION
PROGRAM_ID = 50708  # Splash! 2012
#  the id of the program in the datatree

attended_verb=GetNode('V/Flags/Registration/Attended')


# CHECK-IN USERS
print "Check in Students Live"
print "Newline to terminate"

prog = Program.objects.all().filter(anchor=PROGRAM_ID)[0]

cont = True
while cont:
    i = raw_input()
    if i.strip() == "":
        cont = False
        continue
    
    result = ESPUser.objects.all().filter(id=i)

    if len(result) != 1:
        print "  not found (%s results)" % (len(result))
        continue
    student = result[0]

    # from onsitecheckinmodule.py:
    existing_bits = UserBit.valid_objects().filter(user=student, qsc=prog.anchor, verb=attended_verb)
    if not existing_bits.exists():
        new_bit, created = UserBit.objects.get_or_create(user=student, qsc=prog.anchor, verb=attended_verb)
        print "  %s %s marked as attended." % (student.first_name, student.last_name)
    else:
        print "  already marked as attended"
