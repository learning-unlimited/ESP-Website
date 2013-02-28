from esp.program.models import *

invalid = True

while invalid:
    pid = raw_input("Enter the program name or id number: ")

    try:
    #Let's assume the user's nice and gave us an id number
        pid = int(pid)
        p = Program.objects.get(id=85)
        break
    except ValueError:
    #Meep, the user gave us a string! Let's try to work with that.
        pid = pid.split()
        for p in Program.objects.all():
            reject = False
            for item in pid:
                if not (item in p.niceName()):
                    reject = True
                    break
            if not reject:
                invalid = False #I have a program, I don't need to prompt the user again.
                break
    
    if invalid: print "Error - please try again?"
        
l = []
#p = Program.objects.filter(id=85)[0]

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
