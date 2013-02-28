from esp.program.models import *

PROGRAM_ID = 88    # Spark 2012

classes = Program.objects.filter(id=PROGRAM_ID)[0].classes()

count = 0
hours = 0
for c in classes:
    hasProj = False
    for r in c.getResourceRequests():
        if r.res_type_id is 151:    # Projector resource
            hasProj = True
    
    if hasProj:
       count += 1
       hours += (int(float(c.duration) + 0.5) * c.sections.count())

print "Count: " + str(count)
print "Hours: " + str(hours)
