from __future__ import print_function
from script_setup import *
import sys

if len(sys.argv) < 2:
    print("Usage: {} <program ID> [separator]".format(sys.argv[0]), file=sys.stderr)
    print("You can get program IDs from an admin page, probably /admin/program/program/", file=sys.stderr)
    exit(1)

PROG = int(sys.argv[1])
separator = sys.argv[2] if len(sys.argv) >= 3 else '\n'

print(separator.join(subj.title for subj in ClassSubject.objects.filter(parent_program=Program.objects.get(id=PROG), status__gt=0)))
