#
# Check in Students by Barcode
#
# Performs rapid check-in on a list of students read from a file
# or entered via the shell. Sets Attendance bit only. Make sure
# to update the configuration below.
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


# LOAD DATA
ids = []
ans = raw_input("Read from (F)ile or (S)hell: ")

if ans.lower() == "f":
    filename = raw_input("Filename: ")
    f = open(filename, "r")
    for line in f:
        ids.append(line)
    f.close()

elif ans.lower() == "s":
    print "One id per line, end with a blank line"
    line = " "
    while line != "":
        line = raw_input("")
        ids.append(line)

else:
    print "What? Exiting."
    sys.exit()


# CHECK-IN USERS
prog = Program.objects.all().filter(anchor=PROGRAM_ID)[0]

for i in ids:
    if i.strip() == "":
        continue
    
    result = ESPUser.objects.all().filter(id=i)

    if len(result) != 1:
        print "%s: Not found (%s results)" % (i, len(result))
        continue
    student = result[0]

    # from onsitecheckinmodule.py:
    existing_bits = UserBit.valid_objects().filter(user=student, qsc=prog.anchor, verb=GetNode('V/Flags/Registration/Attended'))
    if not existing_bits.exists():
        new_bit, created = UserBit.objects.get_or_create(user=student, qsc=prog.anchor, verb=GetNode('V/Flags/Registration/Attended'))
        print '%s: %s %s marked as attended.' % (i, student.first_name, student.last_name)
    else:
        print '%s: already marked as attended' % (i)
