from esp.program.models import *

PROGRAM_ID = 88    # Spark 2012

classes = Program.objects.filter(id=PROGRAM_ID)[0].classes()

needs_sound = set()
has_sound = set()

for c in classes:
    if not c.isAccepted():
        continue
    
    for s in c.sections.all():
        for r in s.getResourceRequests():
            if r.res_type_id is 153:	# Sound System
                needs_sound.add(s)
        
        for cr in s.classrooms():
            for r in cr.associated_resources():
                if r.res_type_id is 153:
                    has_sound.add(s)
    
print "Needs Sound System"
print "\n".join([s.__unicode__() + " -- " + ",".join(s.prettyrooms()) + " -- " + str(s.room_capacity()) for s in needs_sound - has_sound])
print
print "Has, but doesn't need, Sound System"
print "\n".join([s.__unicode__() + " -- " + ",".join(s.prettyrooms()) + " -- " + str(s.room_capacity()) for s in has_sound - needs_sound])
