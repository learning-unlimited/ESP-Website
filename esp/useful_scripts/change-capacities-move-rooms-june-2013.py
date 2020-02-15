#
# Update capacities and classrooms of classes
#
# Input: a .csv with
# section code, capacity, room
# where empty is no change.  Make sure it has 3 columns always.
#
# Run me from the manage.py shell
#
# Warning: the class capacity changes may not show up immediately in Ajax scheduling due to some caching bugs.  Even a flush cache doesn't work; I'm not sure what the issue is.  If it's a problem, shift-refresh the page open and re-save it from the admin panel, or be patient.
#
# Warning: if the class does not have a time set, this script will not assign it a room.
#

import csv
from esp.program.models.class_ import ClassSubject
from esp.resources.models import Resource

def makeChanges(filename,override=False):

    secs = []

    with open(filename) as f:
        c = csv.reader(f)
        for row in c:
            emailcode, capacity, room = row
            class_id,sec_id = map(int,emailcode[1:].split('s'))
            cls = ClassSubject.objects.get(id=class_id)
            for s in cls.sections.all():
                if s.index()==sec_id:
                    sec=s
            try:
                secs.append((cls,sec,capacity,room))
            except NameError:
                print "Section %s not found" % emailcode
                raise

    for cls,sec,capacity,room in secs:
        if room is not "":
            cas = sec.classroomassignments()
            print "Removing %s from %s" % (sec.emailcode(), ', '.join([x.resource.name for x in cas]))
            cas.delete()

    for cls,sec,capacity,room in secs:
        if room is not "":
            print "Moving section %s to room %s" % (sec.emailcode(), room)
            # the following is stolen from the manage class page code.  I don't like it, but that page works so I am using it.
            room_res = Resource.objects.filter(name=room)
            if room_res.count() > 0:
                print sec.assign_room(room_res[0])
            else:
                print "I don't like room %s" % room
        print "Marking class %s accepted" % cls.emailcode()
        cls.accept()

    for cls,sec,capacity,room in secs:
        if capacity is not "":
            print "Changing class %s size to %s" % (cls.emailcode(),capacity)
            cls.class_size_max = int(capacity)
            cls.save()
            if override:
                sec.max_class_capacity = int(capacity)
                sec.save()
