#!/usr/bin/env python2
#
# Calculate the Intersection Between Two Programs' Students
#

from script_setup import *

splash = Program.objects.get(id=115)
cascade = Program.objects.get(id=118)

ss = set(splash.students()['classreg'])
cs = set(cascade.students()['enrolled'])

result = ss.intersection(cs)
for u in result:
	print "%s <%s>" % (u.name(), u.email)

