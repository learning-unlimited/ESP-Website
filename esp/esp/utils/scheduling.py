#!/usr/bin/python

import sys
from collections import defaultdict
from datetime import datetime,date,time
from esp.program.models import *
from esp.users.models import *
from decimal import Decimal
from xlwt import Workbook,Style


p = None # program
students = None # QuerySet of students in p
sections = None # QuerySet of sections in p
timeslots = None # QuerySet of events in p
priorities = []
ranks = (10, 5) # 10 == approved for class, 5 == maybe, 0 == rejected, None == no application questions
class_assignments = {}
student_assignments = {}
student_preferences = {}
priority_assigned = {}
class_sizes = {}
done = {}
students_f = {}
section = None #debugging
errors = {}
enrolled_in_no_classes = []
num_applied_for = {}
num_enrolled_in = {}
never_registered = set()
NOW = datetime.now()
priorityLimit = 1


def getRankInClass(student, section):
    global NOW
    if not StudentAppQuestion.objects.filter(subject=section.parent_class).count():
        return 10
    elif StudentRegistration.objects.filter(section=section, relationship__name="Rejected",end_date__gte=NOW,user=student).count() or not student.studentapplication_set.filter(program = section.parent_class.parent_program).count():
        return 1
    for sar in StudentAppResponse.objects.filter(question__subject=section.parent_class, studentapplication__user=student):
        if not len(sar.response.strip()):
            return 1
    rank = max(list(StudentAppReview.objects.filter(studentapplication__user=student, studentapplication__program=section.parent_program, reviewer__in=section.teachers).values_list('score', flat=True)) + [-1])
    if rank == -1:
        rank = 10
    return rank

def main(): 
    
    global p, students, sections, timeslots, priorities, ranks, class_assignments, student_assignments, student_preferences, class_sizes, done, students_f, NOW
    global priority_assigned, num_applied_for, num_enrolled_in, never_registered, priorityLimit
    global student #debugging
    
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
#    DO THIS LATER
#    program_name = None
#    program_year = None
#    program_season = None
#    PROGRAM = None

#    for arg in sys.argv[1:]:
#        if PROGRAM is None:
#            PROGRAM = arg
#        else:
#            PROGRAM += " " + arg

#    print PROGRAM

#    print __name__

#    #for arg in sys.argv:
#    #    if "--prog=" in arg:
#    #        program_name = arg[arg.find("=")+1:]
#    #    elif "--year=" in arg:
#    #        program_year = arg[arg.find("=")+1:]
#    #    elif "--season=" in arg:
#    #        program_season = arg[arg.find("=")+1:]
#    #
#    #print "Program Year ==", program_year
#    #print "Program Name ==", program_name
#    #print "Program Season == ", program_season

#    for program in Program.objects.order_by('-id'):
#        if PROGRAM in program.__str__():
#            p = program
#            
#    if p is None:
#        print "The program you specified does not match any in ESP's database." 
#        print "Perhaps you mistyped something?\n"
#        print "Here is a list of the 10 most recently created ESP Programs." 
#        print "If your program matches one of these,"
#        print "restart the script with the correct spelling.\n"
#        for p in Program.objects.order_by('-id')[:10]:
#            print p
#        return

#    print p
#    DO THIS LATER

#    p = Program.objects.order_by('-id')[1]  # HSSP Spring 2011, as of this writing
    
    iscorrect = raw_input("Is this the correct program (y/[n])? ")
    if not (iscorrect.lower() == 'y' or iscorrect.lower() == 'yes'):
        return
        
    if save_enrollments:
        iscorrect = raw_input("Are you sure you want to save the results in the database (y/[n])? ")
        if not (iscorrect.lower() == 'y' or iscorrect.lower() == 'yes'):
            return
    
    print "Setup..." , 
    
    studentregmodule = p.getModuleExtension('StudentClassRegModuleInfo')
    if studentregmodule and studentregmodule.priority_limit > 0:
        priorityLimit = studentregmodule.priority_limit
    students = set()
    for student in set(p.students()['classreg']) | set(p.students()['student_profile']) | set(p.students()['studentapps']):
        students.add(ESPUser(student))
    students = list(students)
    sections = p.sections().filter(status=10)
    timeslots = p.getTimeSlots()
    
    for section in sections:
        class_sizes[section] = section.capacity# - section.num_students() #technically the subtraction isn't necessary
        class_assignments[section] = []
        class_assignments[section.parent_class] = []
        done[section] = False
    for student in students:
        student_assignments[student] = {}
        student_preferences[student] = {}
        priority_assigned[student] = {}
        num_applied_for[student] = 0
        num_enrolled_in[student] = 0
        for timeslot in timeslots:
            student_assignments[student][timeslot] = None
            student_preferences[student][timeslot] = {}
            priority_assigned[student][timeslot] = priorityLimit+1
    
    priorities = [('Priority/'+str(priority)) for priority in range(1,1+priorityLimit)]
    
    for priority in priorities:
        students_f[priority] = {}
        for section in sections:
            students_f[priority][section] = []
            sr_filter = StudentRegistration.objects.filter(section=section, relationship__name=priority, end_date__gte=NOW).distinct()
            for sr in sr_filter:
                students_f[priority][section].append(sr.user)
                # = [sr.user for sr in StudentRegistration.objects.filter(section=section, relationship__name=priority,end_date__gte=datetime.now()).distinct()]
            for student in students_f[priority][section]:
                student_preferences[student][section.get_meeting_times()[0]][priority] = section
    
    print "complete!\n"
    print "Running lottery... ",
    
    for rank in ranks:
        for priority in priorities:
            for section in sections:
                if done[section]:
                    continue
                students_new = []
                for student in students_f[priority][section]:
                    if (student_assignments[student][section.get_meeting_times()[0]] is None) and (getRankInClass(student, section) == rank) and (student not in class_assignments[section.parent_class]):
                        students_new.append(student)
                if len(students_new) + len(class_assignments[section]) > class_sizes[section]:
                    random.shuffle(students_new)
                    students_new = students_new[:(class_sizes[section] - len(class_assignments[section]))]
                    done[section] = True
                class_assignments[section] += students_new
                class_assignments[section.parent_class] += students_new
                for student in students_new:
                    student_assignments[student][section.get_meeting_times()[0]] = section    
                    priority_assigned[student][section.get_meeting_times()[0]] = int(priority[-1])
    
    print "complete!\n"
    if save_enrollments:
        print "Writing output and saving enrollments... ",
    else: 
        print "Writing output... ",
    
    f = open("scheduling.output.txt", "w")
    
    f.write("Enrollment lottery for "+str(p)+" was run at "+str(NOW)+".\n\n\n")
    
    for timeslot in timeslots:
        errors[timeslot] = []
    
    for student in students:
        s = student.username + " ["
        firstTimeslot = True
        for timeslot in timeslots:
            if not firstTimeslot:
                s += ", "
            try:
                s += "[" + str(student_assignments[student][timeslot].parent_class.anchor.name) + ", ["
            except:
                s += "[None, ["
            firstPriority = True
            for priority in priorities:
                if not firstPriority:
                    s += ", "
                if priority in student_preferences[student][timeslot].keys():
                    s += str(student_preferences[student][timeslot][priority].parent_class.anchor.name)
                else:
                    s += "None"
                firstPriority = False
            firstTimeslot = False
            s += "]]"
        s += "] ["
        firstTimeslot = True
        num_classes = 0
        num_preferences = 0
        std_err = ""
        for timeslot in timeslots:
            if not firstTimeslot:
                s += ", "
            num_classes_now = 0
            num_preferences_now = 0
            try:
                t = student_assignments[student][timeslot].id
                s += "1/"
                num_classes += 1
                num_classes_now = 1
            except:
                s += "0/"
            num_preferences_now = len(student_preferences[student][timeslot])
            num_preferences += num_preferences_now
            s += str(num_preferences_now)
            firstTimeslot = False
            if num_preferences_now and not num_classes_now:
                errors[timeslot].append(student)
        s += "] " + str(num_classes) + "/" + str(num_preferences)
        if num_preferences: 
            if not num_classes:
                enrolled_in_no_classes.append(student)
            f.write(s+"\n")
        else:
            never_registered.add(student)
    
    f.write("\n\n\n")
    
    students = list(set(students) - never_registered)
    
    for timeslot in timeslots:
        f.write("The following "+str(len(errors[timeslot]))+" students are not enrolled in any classes during the timeslot "+str(timeslot)+": \n")
        f.write(str([str(student.username) for student in errors[timeslot]])+"\n\n")
    
    f.write("The following "+str(len(enrolled_in_no_classes))+" students are not enrolled in any classes: \n")
    f.write(str([str(student.username) for student in enrolled_in_no_classes]))
    
    f.write("\n\n\n")
    
    wb = {}
    for timeslot in timeslots:
        wb[timeslot] = Workbook()
        f.write("\n"+str(timeslot)+"\n\n\n")
        for section in sections:
            if section.get_meeting_times()[0] == timeslot:
                i = 0
                f.write(str(section)+": "+str(len(class_assignments[section]))+"/"+str(class_sizes[section])+"\n")
                f.write(str([str(student.username) for student in class_assignments[section]])+"\n\n")
                ws = wb[timeslot].add_sheet(section.parent_class.anchor.name)
                ws.row(i).set_cell_text(0, "Username")
                ws.row(i).set_cell_text(1, "Grade")
                ws.row(i).set_cell_text(2, "Email")
                ws.row(i).set_cell_text(3, "Current Enrollment Status")
                ws.row(i).set_cell_text(4, "Rank")
                i += 1
                for priority in priorities:
                    for student in students_f[priority][section]:
                        rank = getRankInClass(student, section)
                        ws.row(i).set_cell_text(0, student.username)
                        ws.row(i).set_cell_number(1, student.getGrade(p))
                        ws.row(i).set_cell_text(2, student.email)
                        ws.row(i).set_cell_number(4, rank)
                        if student_assignments[student][timeslot] == section:
                            ws.row(i).set_cell_text(3, "Enrolled")
                            if save_enrollments:
                                section.preregister_student(student)
                        elif rank != 1:
                            if priority_assigned[student][timeslot] < int(priority[-1]):
                                ws.row(i).set_cell_text(3, priority)
                            else: 
                                ws.row(i).set_cell_text(3, priority + " Waitlist")
                                if save_enrollments:
                                    sr = StudentRegistration()
                                    sr.section = section
                                    sr.user = student
                                    sr.relationship = RegistrationType.objects.get(name="Waitlist/"+str(priority[-1]))
                                    sr.start_date = NOW
                                    sr.save()
                        else:
                            ws.row(i).set_cell_text(3, "Rejected")
                        i += 1
    
    f.write("\n\n\nThe following "+str(len(never_registered))+" students started the profile, but never registered:\n")
    f.write(str([str(user.username) for user in never_registered]))
    f.close()
    i = 0
    for timeslot in timeslots:
        wb[timeslot].save('Timeslot'+str(i+1)+'.xls')
        i += 1
    
    print "complete!\n"
    
    return 0
    
if __name__ == "__main__":
    #Run as main program
    main()
