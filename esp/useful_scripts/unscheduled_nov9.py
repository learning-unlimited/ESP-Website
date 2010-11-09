""" See if there are any unscheduled sections of approved classes
    that have students enrolled in them.
"""

from esp.program.models import *

splash = Program.objects.get(id=12)

for cs in splash.sections():
    if cs.parent_class.status > 0 and (len(cs.timeslot_ids()) == 0 or len(cs.initial_rooms()) == 0) and cs.num_students() > 0:
        print 'Unscheduled: %s' % cs
        print ' -> %d/%d students' % (cs.num_students(), cs.capacity)
        print ' -> Times: %s' % cs.friendly_times()
        print ' -> Rooms: %s' % cs.initial_rooms()
        print ' -> Status: %d (parent class: %d)' % (cs.status, cs.parent_class.status)


