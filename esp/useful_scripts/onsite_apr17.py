from esp.program.models import *
from esp.datatree.models import *
from esp.users.models import *

import string

def ascii_sanitize(s):
    return filter(lambda x: x in string.printable, s)

def dateonly(d):
    return d.strftime('%Y-%m-%d')

def timeonly(d):
    return d.strftime('%H:%M:%S')

splash = Program.objects.get(id=11)

outfile = open('/home/pricem/splash_sp10_checkin.csv', 'w')
filter_verb = DataTree.get_by_uri('V/Flags/Registration/Attended')
teacher_usernames = ['danzaha', 'mshaw', 'estersohnad', 'zamfi', 'havasi', 'scico', 'rtkraw']

appropriate_sections = []
for un in teacher_usernames:
    teacher = ESPUser.objects.get(username=un)
    appropriate_sections += list(teacher.getTaughtSections(splash))

"""
print 'Checking for students in these sections:'
for sec in appropriate_sections:
    print ' -> %s: %s' % (sec.teachers, sec.title())
"""

bits = UserBit.valid_objects().filter(verb=filter_verb,qsc=splash.anchor).order_by('startdate')

outfile.write('"Checkin date","Checkin time","Student first name","Student last name","Student email","Teacher","Class code","Subject","Parent first name","Parent last name","Parent email","Street","City","State","Zip code"\n')
student_list = [ESPUser(bit.user) for bit in bits]
for i in range(len(student_list)):
    student = student_list[i]
    bit = bits[i]
    #   print 'Checking student: %s' % student
    for sec in student.getEnrolledSections(splash):
        if sec in appropriate_sections:
            prof = student.getLastProfile()
            print 'Found %s in %s' % (student, sec)
            #   First, last, student email,
            if prof.contact_user:
                cu = prof.contact_user
            else:
                cu = ContactInfo()
            if prof.contact_guardian:
                cg = prof.contact_guardian
            else:
                cg = ContactInfo()
            tl = ', '.join([ESPUser(t).name() for t in sec.teachers])
            outfile.write('"%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s","%s"\n' % (dateonly(bit.startdate), timeonly(bit.startdate), cu.first_name, cu.last_name, cu.e_mail, tl, sec.emailcode(), ascii_sanitize(sec.title()), cg.first_name, cg.last_name, cg.e_mail, cu.address_street, cu.address_city, cu.address_state, cu.address_zip))


outfile.close()
