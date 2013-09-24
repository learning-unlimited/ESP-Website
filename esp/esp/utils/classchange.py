#!/usr/bin/python

import sys
from collections import defaultdict
from datetime import datetime,date,time
from esp.program.models import *
from esp.users.models import *
from decimal import Decimal
from xlwt import Workbook,Style
from django.db.models import Q
import Queue
import time

p = None # program
timeslots = None
NOW = datetime.now()
priorityLimit = 1
SR_PROG = None
SR_REQ = None
SR_WAIT = None
SR_EN = None
PROG = None
REQ = None
WAIT = None
EN = None
students = []
student = None
sections = []
timeslot = None
en = {}
req = {}
loc = {}
en_new = {}
cap = {}
score = {}
req_num = {}
wait = {}
all_students = set()
changed = set()
unchanged = set()

def get_student_schedule(student):
    global p, timeslots
    """ generate student schedules """
    schedule = "<table border='1'>\n<tr>\n<th>Time and Room</th>\n<th>Class and Teacher</th>\n<th>Code</th>\n</tr>\n"
    for timeslot in timeslots: 
        for cls in student.getSections(p, ["Enrolled"]):
            if cls.get_meeting_times()[0] == timeslot:
                schedule += "<tr>\n<td>"+timeslot.pretty_time()+"<br />"+", ".join(cls.prettyrooms())+"</td>\n<td>"+cls.title()+"<br />"+", ".join(cls.parent_class.getTeacherNames())+"</td>\n<td>"+cls.emailcode()+"</td>\n</tr>\n"
    schedule += "</table>\n"
    return schedule

def main(): 
    
    global NOW, priorityLimit, SR_PROG, SR_REQ, SR_WAIT, SR_EN, PROG, REQ, WAIT, EN, p, students, sections, timeslots, timeslot, all_students
    global en, req, loc, en_new, cap, score, req_num, wait, changed, unchanged, student
    
    save_enrollments = False
    send_emails = False
    
    if "-h" in sys.argv or "--help" in sys.argv:
        print "Help."
        return

    if "--save-enrollments" in sys.argv or "-se" in sys.argv:
        save_enrollments = True
    
    if "--send-emails" in sys.argv:
        send_emails = True

    p = None
    
    for arg in sys.argv:
        if arg.startswith("--pk="):
            p = Program.objects.get(pk=int(arg[5:]))
            break
    if not p:
        return
    else:
        print p
    
    iscorrect = raw_input("Is this the correct program (y/[n])? ")
    if not (iscorrect.lower() == 'y' or iscorrect.lower() == 'yes'):
        return
        
    if save_enrollments:
        iscorrect = raw_input("Are you sure you want to save the results in the database (y/[n])? ")
        if not (iscorrect.lower() == 'y' or iscorrect.lower() == 'yes'):
            return
    
    studentregmodule = p.getModuleExtension('StudentClassRegModuleInfo')
    if studentregmodule and studentregmodule.priority_limit > 0:
        priorityLimit = studentregmodule.priority_limit
    SR_PROG = Q(studentregistration__section__parent_class__parent_program=p, studentregistration__start_date__lte=NOW, studentregistration__end_date__gte=NOW)
    SR_REQ = Q(studentregistration__relationship__name="Request") & SR_PROG
    SR_WAIT = [Q(studentregistration__relationship=("Waitlist/%s" % str(i+1))) & SR_PROG for i in range(priorityLimit)]
    SR_WAIT.append(Q(studentregistration__relationship__contains="Waitlist") & SR_PROG)
    SR_EN = Q(studentregistration__relationship__name="Enrolled") & SR_PROG
    PROG = Q(section__parent_class__parent_program=p, start_date__lte=NOW, end_date__gte=NOW)
    REQ = Q(relationship__name="Request") & PROG
    WAIT = [Q(relationship__name__contains="Waitlist") & PROG]
    WAIT += [Q(relationship__name=("Waitlist/%s" % str(i+1))) & PROG for i in range(priorityLimit)]
    EN = Q(relationship__name="Enrolled") & PROG
    timeslots = p.getTimeSlots()

    for timeslot in timeslots: 
        print "Setup for", timeslot, "....",
        sys.stdout.flush()
        en = {}
        req = {}
        loc = {}
        en_new = {}
        cap = {}
        score = {}
        req_num = {}
        wait = {}
        sections = list(p.sections().filter(status=10, meeting_times=timeslot))
        class ClassSectionNull:
            def __init__(self):
                self.limbo = []
            def __repr__(self):
                return "<NullSection>"
        NullSection = ClassSectionNull()
        en[NullSection] = [[]]
        cap[NullSection] = 0
        score[NullSection] = 0
        for i in range(len(sections)):
            en[sections[i]] = [[] for j in range(priorityLimit+2)] 
            req[sections[i]] = [[] for j in range(priorityLimit+2)]
            en_new[sections[i]] = []
            cap[sections[i]] = sections[i].capacity - sections[i].num_students()
            req_num[sections[i]] = 0
            score[sections[i]] = -cap[sections[i]]
        students = ESPUser.objects.filter(SR_REQ, studentregistration__section__meeting_times=timeslot)
        all_students |= set(students)
        for i in range(students.count()):
            req[students[i]] = StudentRegistration.objects.get(REQ, user=students[i], section__meeting_times=timeslot).section
            loc[students[i]] = StudentRegistration.objects.get(REQ, user=students[i], section__meeting_times=timeslot).section
            req[req[students[i]]][0].append(students[i])
            req_num[req[students[i]]] += 1
            score[req[students[i]]] += 1
            try:
                en[students[i]] = StudentRegistration.objects.get(EN, user=students[i], section__meeting_times=timeslot).section
            except Exception:
                en[students[i]] = NullSection
            en[en[students[i]]][0].append(students[i])
            cap[en[students[i]]] += 1
            score[en[students[i]]] -= 1
            try:
                wait[students[i]] = int(StudentRegistration.objects.get(WAIT[0], user=students[i], section__meeting_times=timeslot, section=req[students[i]]).relationship.name.partition("/")[2])
            except Exception:
                wait[students[i]] = priorityLimit + 1
            req[req[students[i]]][wait[students[i]]].append(students[i])
            en[req[students[i]]][wait[students[i]]].append(students[i])
        cap[NullSection] = 0
        score[NullSection] = 0
        print " done!"
        print "Randomly assigning students to classes by priority ....", 
        sys.stdout.flush()
        for i in range(len(sections)):
            for j in range(1, priorityLimit+2): 
                if len(en[sections[i]][j]) > cap[sections[i]]:
                    random.shuffle(en[sections[i]][j])
                    for k in range(cap[sections[i]], len(en[sections[i]][j])):
                        NullSection.limbo.append(en[sections[i]][j][k])
                        loc[en[sections[i]][j][k]] = NullSection
                    en[sections[i]][j] = en[sections[i]][j][:(cap[sections[i]])]
                    for k in range(j+1, priorityLimit+2): 
                        for l in range(len(en[sections[i]][k])):
                            NullSection.limbo.append(en[sections[i]][k][l])
                            loc[en[sections[i]][k][l]] = NullSection
                        en[sections[i]][k] = []
                cap[sections[i]] -= len(en[sections[i]][j])
                en_new[sections[i]] += en[sections[i]][j]
                if not cap[sections[i]]:
                    break
        print " done!"
        print "Pushing students back to original classes...", 
        sys.stdout.flush()
        a = 0
        limbo_orig = NullSection.limbo[:]
        limbo_all = [set()]
        
        while len(NullSection.limbo): 
            a += 1
            limbo_all.append(set())
            limbo_old = NullSection.limbo[:]
            NullSection.limbo = []
            for i in range(len(limbo_old)): 
                limbo_all[0].add(limbo_old[i])
                limbo_all[a].add(limbo_old[i])
                if en[limbo_old[i]] == NullSection:
                    continue
                if isinstance(en_new[en[limbo_old[i]]], list) and len(en_new[en[limbo_old[i]]]): 
                    pq = Queue.PriorityQueue()
                    random.shuffle(en_new[en[limbo_old[i]]])
                    b = 0
                    for student in en_new[en[limbo_old[i]]]:
                        pq.put((score[en[student]], student), False)
                        b += 1
                    en_new[en[limbo_old[i]]] = pq
                if not cap[en[limbo_old[i]]]: 
                    move = en_new[en[limbo_old[i]]].get(False)[1]
                    sys.stdout.flush()
                    loc[move] = NullSection
                    NullSection.limbo.append(move)
                else:
                    cap[en[limbo_old[i]]] -= 1
                loc[limbo_old[i]] = en[limbo_old[i]]
        print " done!"
        print "Saving enrollments ....",
        sys.stdout.flush()
        for student in students:
            if loc[student] != en[student] and loc[student] != NullSection: 
                if save_enrollments:
                    loc[student].preregister_student(student)
                    if en[student] != NullSection:
                        en[student].unpreregister_student(student)
                changed.add(student)
            else:
                unchanged.add(student)
        print " done!\n\n"
        sys.stdout.flush()
    unchanged -= changed
    
    print "Sending emails...."
    from django.conf import settings
    if hasattr(settings, 'EMAILTIMEOUT') and \
           settings.EMAILTIMEOUT is not None:
        timeout = settings.EMAILTIMEOUT
    else:
        timeout = 2
    f = open("classchanges.txt", 'w')
    from esp.dbmail.models import send_mail, MessageRequest, TextOfEmail
    subject = "[" + p.niceName() + "] Class Change"
    from_email = p.director_email
    bcc = p.getDirectorCCEmail()
    extra_headers = {}
    extra_headers['Reply-To'] = p.director_email
    for student in changed:
        text = "<html>\nHello "+student.first_name+",<br /><br />\n\n"
        text += "We've processed your class change request, and have updated your schedule. Your new schedule is as follows: <br /><br />\n\n"
        text += get_student_schedule(student)+"\n\n<br /><br />\n\n"
        text += "We hope you enjoy your new schedule. See you soon!<br /><br />"
        text += "The " + p.niceName() + " Directors\n"
        text += "</html>"
        recipient_list = [student.email]
        print text, "\n\nSent to", student.username, "<", student.email, ">\n\n------------------------\n\n"
        f.write(text.replace(u'\u2019', "'").replace(u'\u201c','"').replace(u'\u201d','"')+"\n\nSent to "+student.username+"\n\n------------------------\n\n")
        if save_enrollments and send_emails:
            send_mail(subject, text, from_email, recipient_list, bcc=bcc, extra_headers=extra_headers)
            time.sleep(timeout)
    
    for student in unchanged:
        text = "<html>\nHello "+student.first_name+",<br /><br />\n\n"
        text += "We've processed your class change request, and unfortunately are unable to update your schedule. Your schedule is still as follows: <br /><br />\n\n"
        text += get_student_schedule(student)+"\n\n<br /><br />\n\n"
        text += "See you soon!<br /><br />"
        text += "The " + p.niceName() + " Directors\n"
        text += "</html>"
        recipient_list = [student.email]
        print text, "\n\nSent to", student.username, "<", student.email, ">\n\n------------------------\n\n"
        f.write(text.replace(u'\u2019', "'").replace(u'\u201c','"').replace(u'\u201d','"')+"\n\nSent to "+student.username+"\n\n------------------------\n\n")
        if save_enrollments and send_emails:
            send_mail(subject, text, from_email, recipient_list, bcc=bcc, extra_headers=extra_headers)
            time.sleep(timeout)

    return 0
    
if __name__ == "__main__":
    #Run as main program
    main()
