#!/usr/bin/env python

from esp.program.models import *

splash=Program.objects.get(id=12)

rooms = splash.getClassrooms()

num_conflicts = 0
for r in rooms:
    ct = r.resourceassignment_set.count()
    if ct == 1:
        print r.name, r.event.pretty_time(), r.resourceassignment_set.all()[0].target.title()
    elif ct > 1:
        print 'ERROR: %s at %s has conflict: %s' % (r.name, r.event.pretty_time(), r.resourceassignment_set.all().values_list('target', flat=True))
        num_conflicts += 1




print ' '
print 'Found %d conflicts.' % num_conflicts
