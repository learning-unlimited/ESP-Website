""" Scheduling problem generator
    Michael Price (price@kilentra.net)
"""

#   Run-specific stuff
prog_id = 11
filename = '/home/pricem/scheduling/scheduling_%d.txt' % prog_id
#   End of run-specific stuff

from esp.program.models import *
import string
import cgi

"""
<block id=0 name="10-11 AM" />
<resource id=0 fixed=1 name="Chalkboard" />
<room id=0 name="6-103" capacity=20>
    <has-resource id=0 />
</room>
<resource id=1 fixed=0 name="Projector" avail=5 />
<teacher id=52 name="Louis Wasserman">
    <available block=2 />
    <available block=3 />
</teacher>
<class id=50 regID="C1500" name="Computing for n00bs" cap=25 sections=2 duration=1>
    <needs-resource id=1 qty=1 />
    <class-teacher id=52 />
    <class-teacher id=5 />
</class>
"""

file = open(filename, 'w')

prog = Program.objects.get(id=prog_id)
teachers = [ESPUser(x) for x in prog.teachers()['class_approved']]

#   Get blocks
#   <block id=0 name="10-11 AM" />
blocks = prog.getTimeSlots()
for block in blocks:
    file.write('<block id=%d name="%s" />\n' % (block.id, block.pretty_time()))
file.write('\n')

#   Get resource types.
#   <resource id=0 fixed=1 name="Chalkboard" />
restypes = prog.getResourceTypes().exclude(name="Teacher Availability")
for restype in restypes:
    file.write('<resource id=%d fixed=1 name="%s" />\n' % (restype.id, restype.name))
file.write('\n')

#   Get rooms and fixed resources
#   NOTE: Assumes all rooms will be available for the entire program.
#   <room id=0 name="6-103" capacity=20>
#       <has-resource id=0 />
#   </room>
rooms = prog.getClassrooms()
room_names_so_far = []
for room in rooms:
    if room.name not in room_names_so_far:
        file.write('<room id=%d name="%s" capacity=%d>\n' % (room.id, cgi.escape(room.name), room.num_students))
        for resource in room.associated_resources():
            file.write('  <has-resource id=%d />\n' % resource.res_type.id)
        file.write('</room>\n')
        room_names_so_far.append(room.name)
file.write('\n')

#   Get floating resources
#   <resource id=1 fixed=0 name="Projector" avail=5 />
floating_resources = prog.getAvailableResources(prog.getTimeSlots()[0])
for resource in floating_resources:
    file.write('<resource id=%d fixed=0 name="%s" avail=1 />\n' % (resource.id, cgi.escape(resource.name)))
file.write('\n')

#   Get teacher availability
#   <teacher id=52 name="Louis Wasserman">
#       <available block=2 />
#       <available block=3 />
#   </teacher>

for teacher in teachers:
    file.write('<teacher id=%d name="%s">\n' % (teacher.id, cgi.escape(teacher.name())))
    available_times = teacher.getAvailableTimes(prog)
    for timeslot in available_times:
        file.write('  <available block=%d />\n' % timeslot.id)
    file.write('</teacher>\n')
file.write('\n')

#   Get classes
#   <class id=50 regID="C1500" name="Computing for n00bs" cap=25 sections=2 duration=1>
#       <needs-resource id=1 qty=1 />
#       <class-teacher id=52 />
#       <class-teacher id=5 />
#   </class>
classes = prog.classes()
for cls in classes:
    sec = cls.default_section()
    title_sanitized = cgi.escape(filter(lambda x: x in string.printable, cls.title())).replace('"', '&quot;')
    file.write('<class id=%d regID="%s" category="%s" name="%s" cap=%d sections=%d duration=%d>\n' % (cls.id, cls.emailcode(), cls.category.category, title_sanitized, sec.max_class_capacity or cls.class_size_max, cls.sections.count(), int(float(sec.duration) + 0.5)))
    for rr in sec.getResourceRequests():
        file.write('  <needs-resource id=%d qty=1 />\n' % rr.res_type.id)
    for teacher in cls.teachers():
        file.write('  <class-teacher id=%d />\n' % teacher.id)
    file.write('</class>\n')
file.write('\n')

file.close()

print 'Wrote output to %s' % filename
