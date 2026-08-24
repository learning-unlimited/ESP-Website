#!/usr/bin/env python2
#
# Get a list of all students who marked a given class subject as starred
# or interested.
#

import sys

from script_setup import *

if len(sys.argv) != 2:
    print "usage: %s numeric-subject-id" % sys.argv[0]
    exit()

subj = ClassSubject.objects.get(id=int(sys.argv[1]))
secs = subj.get_sections()
print "Program: %s" % subj.parent_program.name
print "Class Subject: %s (%d sections)" % (subj.title, len(secs))
print ""

starred = set(ESPUser.objects.get(id=d['user_id']) \
	      for d in subj.studentsubjectinterest_set.values())
interested = set()
for sec in secs:
    interested.update(ESPUser.objects.get(id=d['user_id']) \
		      for d in sec.studentregistration_set.values())

print "PRIORITY STUDENTS (%d)" % len(interested)
print "\n".join("%s <%s>" % (u.name(), u.email) for u in interested)

print ""

print "NON-PRIORITY STUDENTS WITH STARS (%d)" % len(starred-interested)
print "\n".join("%s <%s>" % (u.name(), u.email) for u in starred-interested)
