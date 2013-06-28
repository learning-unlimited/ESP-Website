#
# Update capacities and classrooms of classes
#
# Input: a .csv with
# section code, capacity, room
# where empty is no change.  Make sure it has 3 columns always.
#
# Run me from the manage.py shell
#

import csv
from esp.program.models.class_ import ClassSection, ClassSubject
from esp.resources.models import Resource

filename = '/home/ben/Documents/esp-website/hssp-capacities.csv'

with open(filename) as f:
    c = csv.reader(f)
    for row in c:
        emailcode, capacity, room = row
        class_id,sec_id = map(int,emailcode[1:].split('s'))
        cls = ClassSubject.objects.get(id=class_id)
        for s in cls.sections.all():
            if s.index()==sec_id:
                sec=s
        print "Operating on section %s of class %s" % (sec,cls)
        if capacity is not "":
            print "Changing class %s size to %s" % (cls.emailcode(),capacity)
            cls.class_size_max = int(capacity)
            cls.save()
        if room is not "":
            print "Moving section %s to room %s" % (sec.emailcode(), room)
            # the following is stolen from the manage class page code.  I don't like it, but that page works so I am using it.
            room_res = Resource.objects.filter(name=room)
            if room_res.count() > 0:
                sec.classroomassignments().delete()
                print sec.assign_room(room_res[0])
            else:
                print "I don't like room %s" % room
            

