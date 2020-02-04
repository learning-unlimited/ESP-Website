from __future__ import print_function
from script_setup import *
import sys

if len(sys.argv) < 2:
    print("Usage: {} <program ID> [<increment>]".format(sys.argv[0]), file=sys.stderr)
    print("You can get program IDs from an admin page, probably /admin/program/program/", file=sys.stderr)
    exit(1)

PROG = int(sys.argv[1])
increment = int(sys.argv[2]) if len(sys.argv) >= 3 else 1

prog = Program.objects.get(id=PROG)

print("Extending walkins for program {} by {} hour(s)...".format(prog.name, increment), file=sys.stderr)

walkins = ClassSection.objects.filter(parent_class__parent_program__id=PROG, parent_class__category=prog.open_class_category)

for w in walkins:
    w.duration += increment
    w.save()

print("Done!", file=sys.stderr)
