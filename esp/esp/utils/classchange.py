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

def main(): 
    
    global NOW, priorityLimit, SR_PROG, SR_REQ, SR_WAIT, SR_EN, PROG, REQ, WAIT, EN, p, students, sections, timeslots, timeslot
    global en, req, loc, en_new, cap, score, req_num, wait
    
    save_enrollments = False
    
    if "-h" in sys.argv or "--help" in sys.argv:
        print "Help."
        return

    if "--save-enrollments" in sys.argv or "-se" in sys.argv:
        save_enrollments = True
    
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
           ################     
        a = 0
        #del en[NullSection]
        #print en
        #del req[NullSection]
        #print req
        #del loc[NullSection]
        #print loc
        #del en_new[NullSection]
        #print en_new
        #del cap[NullSection]
        #print cap
        #del score[NullSection]
        #print score
        #del req_num[NullSection]
        #print req_num
        #del wait[NullSection]
        #print wait
        #return 0
        
        limbo_orig = NullSection.limbo[:]
        limbo_all = [set()]
        
#        print cap
        
        while len(NullSection.limbo): 
#            print a
#            sys.stdout.flush()
            a += 1
            limbo_all.append(set())
            limbo_old = NullSection.limbo[:]
            NullSection.limbo = []
            for i in range(len(limbo_old)): 
#                print "\t", i
#                sys.stdout.flush()
                limbo_all[0].add(limbo_old[i])
                limbo_all[a].add(limbo_old[i])
                if en[limbo_old[i]] == NullSection:
                    continue
                if isinstance(en_new[en[limbo_old[i]]], list) and len(en_new[en[limbo_old[i]]]): 
#                    print "test0", 
#                    sys.stdout.flush()
                    pq = Queue.PriorityQueue()
#                    print "test1", 
#                    sys.stdout.flush()
                    random.shuffle(en_new[en[limbo_old[i]]])
#                    print "test2", 
#                    sys.stdout.flush()
                    b = 0
                    for student in en_new[en[limbo_old[i]]]:
#                        print (score[en[student]], student)
#                        sys.stdout.flush()
                        pq.put((score[en[student]], student), False)
#                        print "\t\t", b
#                        sys.stdout.flush()
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
#        print "\n\n\n", timeslot
        for student in students:
            if loc[student] == en[student]: 
                pass
#                print student, "-", en[student], ">>", req[student], ">>", loc[student]
            else:
#                print student, "-", en[student], ">>", loc[student]
                if loc[student] == NullSection:
                    pass
#                    print "\t", en[student], ">>", req[student], ">>", loc[student]
#                    print "\t", (student in limbo_all[0])
#                    for i in range(1,len(limbo_all)):
#                        if student in limbo_all[i]:
#                            print "\t", i
                elif save_enrollments:
                    loc[student].preregister_student(student)
                    if en[student] != NullSection:
                        en[student].unpreregister_student(student)
#        print cap
#        print "\n\n\n"
                
#    for student in students:
#        student_assignments_original[student] = {}
#        for timeslot in timeslots:
#            student_assignments_original[student][timeslot] = None
#            student_preferences_final[student][timeslot] = None
#    
#    for section in sections:
#        class_assignments_original[section] = students.filter(id__in=[students.id for student in section.students()])
#        class_assignments_final[section] = [class_assignments_original[section].exclude(studentregistration__section__meeting_times=section.get_meeting_times()[0], REQ)]
#        class_sizes[section] = len(class_assignments_original)
#        class_assignments_original[section.parent_class] += list(class_assignments_original)
#        class_request_priorities[section] = [students.filter(studentregistration__section=section, WAIT[i], REQ) for i in range(priorityLimit)]
#        class_request_priorities[section].append(students.filter(studentregistration__section=section, REQ).exclude(studentregistration__section=section, WAIT[-1]))
#        sections_by_timeslot[section.get_meeting_times()[0]].append(section)
#    
#    print "complete!\n"
#    print "Running lottery... ",
#    
#    for timeslot in timeslots:
#        for section in sections_by_timeslot[timeslot]:
#            
#    
#    print "complete!\n"
#    if save_enrollments:
#        print "Writing output and saving enrollments... ",
#    else: 
#        print "Writing output... ",
#    
#    f = open("scheduling.output.txt", "w")
#    
#    f.write("Enrollment lottery for "+str(p)+" was run at "+str(NOW)+".\n\n\n")
#    
#    for timeslot in timeslots:
#        errors[timeslot] = []
#    
#    for student in students:
#        s = student.username + " ["
#        firstTimeslot = True
#        for timeslot in timeslots:
#            if not firstTimeslot:
#                s += ", "
#            try:
#                s += "[" + str(student_assignments[student][timeslot].parent_class.anchor.name) + ", ["
#            except:
#                s += "[None, ["
#            firstPriority = True
#            for priority in priorities:
#                if not firstPriority:
#                    s += ", "
#                if priority in student_preferences[student][timeslot].keys():
#                    s += str(student_preferences[student][timeslot][priority].parent_class.anchor.name)
#                else:
#                    s += "None"
#                firstPriority = False
#            firstTimeslot = False
#            s += "]]"
#        s += "] ["
#        firstTimeslot = True
#        num_classes = 0
#        num_preferences = 0
#        std_err = ""
#        for timeslot in timeslots:
#            if not firstTimeslot:
#                s += ", "
#            num_classes_now = 0
#            num_preferences_now = 0
#            try:
#                t = student_assignments[student][timeslot].id
#                s += "1/"
#                num_classes += 1
#                num_classes_now = 1
#            except:
#                s += "0/"
#            num_preferences_now = len(student_preferences[student][timeslot])
#            num_preferences += num_preferences_now
#            s += str(num_preferences_now)
#            firstTimeslot = False
#            if num_preferences_now and not num_classes_now:
#                errors[timeslot].append(student)
#        s += "] " + str(num_classes) + "/" + str(num_preferences)
#        if num_preferences: 
#            if not num_classes:
#                enrolled_in_no_classes.append(student)
#            f.write(s+"\n")
#        else:
#            never_registered.add(student)
#    
#    f.write("\n\n\n")
#    
#    students = list(set(students) - never_registered)
#    
#    for timeslot in timeslots:
#        f.write("The following "+str(len(errors[timeslot]))+" students are not enrolled in any classes during the timeslot "+str(timeslot)+": \n")
#        f.write(str([str(student.username) for student in errors[timeslot]])+"\n\n")
#    
#    f.write("The following "+str(len(enrolled_in_no_classes))+" students are not enrolled in any classes: \n")
#    f.write(str([str(student.username) for student in enrolled_in_no_classes]))
#    
#    f.write("\n\n\n")
#    
#    wb = {}
#    for timeslot in timeslots:
#        wb[timeslot] = Workbook()
#        f.write("\n"+str(timeslot)+"\n\n\n")
#        for section in sections:
#            if section.get_meeting_times()[0] == timeslot:
#                i = 0
#                f.write(str(section)+": "+str(len(class_assignments[section]))+"/"+str(class_sizes[section])+"\n")
#                f.write(str([str(student.username) for student in class_assignments[section]])+"\n\n")
#                ws = wb[timeslot].add_sheet(section.parent_class.anchor.name)
#                ws.row(i).set_cell_text(0, "Username")
#                ws.row(i).set_cell_text(1, "Grade")
#                ws.row(i).set_cell_text(2, "Email")
#                ws.row(i).set_cell_text(3, "Current Enrollment Status")
#                ws.row(i).set_cell_text(4, "Rank")
#                i += 1
#                for priority in priorities:
#                    for student in students_f[priority][section]:
#                        rank = getRankInClass(student, section)
#                        ws.row(i).set_cell_text(0, student.username)
#                        ws.row(i).set_cell_number(1, student.getGrade(p))
#                        ws.row(i).set_cell_text(2, student.email)
#                        ws.row(i).set_cell_number(4, rank)
#                        if student_assignments[student][timeslot] == section:
#                            ws.row(i).set_cell_text(3, "Enrolled")
#                            if save_enrollments:
#                                section.preregister_student(student)
#                        elif rank != 1:
#                            if priority_assigned[student][timeslot] < int(priority[-1]):
#                                ws.row(i).set_cell_text(3, priority)
#                            else: 
#                                ws.row(i).set_cell_text(3, priority + " Waitlist")
#                                if save_enrollments:
#                                    sr = StudentRegistration()
#                                    sr.section = section
#                                    sr.user = student
#                                    sr.relationship = RegistrationType.objects.get(name="Waitlist/"+str(priority[-1]))
#                                    sr.start_date = NOW
#                                    sr.save()
#                        else:
#                            ws.row(i).set_cell_text(3, "Rejected")
#                        i += 1
#    
#    f.write("\n\n\nThe following "+str(len(never_registered))+" students started the profile, but never registered:\n")
#    f.write(str([str(user.username) for user in never_registered]))
#    f.close()
#    i = 0
#    for timeslot in timeslots:
#        wb[timeslot].save('Timeslot'+str(i+1)+'.xls')
#        i += 1
#    
#    print "complete!\n"
    
    return 0
    
if __name__ == "__main__":
    #Run as main program
    main()
