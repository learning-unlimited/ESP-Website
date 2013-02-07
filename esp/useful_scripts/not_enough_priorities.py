from esp.program.models import *

l = []
p = Program.objects.filter(id=85)[0]

for s in p.students()['lotteried_students']:
    student_registrations = StudentRegistration.objects.filter(section__parent_class__parent_program=p,end_date__gt=datetime.now(),user=s).distinct()
    student_sections = [r.section for r in student_registrations]
    number = len(student_sections)
    timeblocks = len(set([sec.start_time() for sec in student_sections]))
    if number/timeblocks < 3:
        l.append(s.email)

for e in l:
    print e + ","

print len(l)

#section__parent_class__parent_pragram=p
