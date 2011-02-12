#!/usr/bin/python

import sys
from collections import defaultdict
from datetime import datetime
from esp.program.models import *
from esp.users.models import *

p = None # program
students = None # QuerySet of students in p
sections = None # QuerySet of sections in p
timeslots = None # QuerySet of events in p
priorities = [('Priority/'+str(priority)) for priority in range(1,4)]
ranks = (10, 5) # 10 == approved for class, 5 == maybe, 0 == rejected, None == no application questions
class_assignments = {}
student_assignments = {}
student_preferences = {}
class_sizes = {}
done = {}
students_f = {}
section = None #debugging
errors = {}
registered_for_no_classes = []
NOW = datetime.now()
all_student_registrations = []

def getRankInClass(student, section):
    global NOW
    try:
        sr = StudentRegistration.objects.get(section=section, relationship__name="Rejected",end_date__gte=datetime.now(),user=student)
        all_student_registrations.append(sr)
        return 1
    except Exception:
        pass
    rank = max(list(StudentAppReview.objects.filter(studentapplication__user=student, studentapplication__program=section.parent_program, reviewer__in=section.teachers).values_list('score', flat=True)) + [-1])
    if rank == -1:
        rank = 10
    return rank

def main(): 
    
    global p, students, sections, timeslots, priorities, ranks, class_assignments, student_assignments, student_preferences, class_sizes, done, students_f, NOW
    global student #debugging
    
    save_enrollments = False
    
    if "-h" in sys.argv or "--help" in sys.argv:
        print "Help."
        return

    if "--save-enrollments" in sys.argv or "-se" in sys.argv:
        save_enrollments = True

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

    p = Program.objects.order_by('-id')[1]  # HSSP Spring 2011, as of this writing
    
    students = p.students()['classreg']
    sections = p.sections().filter(status=10)
    timeslots = p.getTimeSlots()
    
    for section in sections:
        class_sizes[section] = section.capacity# - section.num_students() #technically the subtraction isn't necessary
        class_assignments[section] = []
        done[section] = False
    for student in students:
        student_assignments[student] = {}
        student_preferences[student] = {}
        for timeslot in timeslots:
            student_assignments[student][timeslot] = None
            student_preferences[student][timeslot] = {}
    
    
    
    for priority in priorities:
        students_f[priority] = {}
        for section in sections:
            students_f[priority][section] = []
            sr_filter = StudentRegistration.objects.filter(section=section, relationship__name=priority,end_date__gte=datetime.now()).distinct()
            for sr in sr_filter:
                students_f[priority][section].append(sr.user)
                # = [sr.user for sr in StudentRegistration.objects.filter(section=section, relationship__name=priority,end_date__gte=datetime.now()).distinct()]
                all_student_registrations.append(sr)
            for student in students_f[priority][section]:
                student_preferences[student][section.get_meeting_times()[0]][priority] = section
    
    for rank in ranks:
        for priority in priorities:
            for section in sections:
                if done[section]:
                    continue
                students_new = []
                for student in students_f[priority][section]:
                    if (student_assignments[student][section.get_meeting_times()[0]] is None) and (getRankInClass(student, section) == rank):
                        students_new.append(student)
                if len(students_new) + len(class_assignments[section]) > class_sizes[section]:
                    random.shuffle(students_new)
                    students_new = students_new[:(class_sizes[section] - len(class_assignments[section]))]
                    done[section] = True
                class_assignments[section] += students_new
                for student in students_new:
                    student_assignments[student][section.get_meeting_times()[0]] = section     
    
    f = open("scheduling.output.txt", "w")
    
    f.write("Enrollment lottery for "+str(p)+" was run at "+str(NOW)+"; this is the end date for all expired StudentRegistrations.\n\n\n")
    
    for timeslot in timeslots:
        errors[timeslot] = []
    
    for student in students:
        s = student.username + " ["
        firstTimeslot = True
        for timeslot in timeslots:
            if not firstTimeslot:
                s += ", "
            try:
                s += "[" + str(student_assignments[student][timeslot].id) + ", ["
            except:
                s += "[None, ["
            firstPriority = True
            for priority in priorities:
                if not firstPriority:
                    s += ", "
                if priority in student_preferences[student][timeslot].keys():
                    s += str(student_preferences[student][timeslot][priority].id)
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
        if not num_classes:
            registered_for_no_classes.append(student)
        f.write(s+"\n")
    
    f.write("\n\n\n")
    
    for timeslot in timeslots:
        f.write("The following "+str(len(errors[timeslot]))+" students are not enrolled in any classes during the timeslot "+str(timeslot)+": \n")
        f.write(str([str(student.username) for student in errors[timeslot]])+"\n\n")
    
    f.write("The following "+str(len(registered_for_no_classes))+" students are not enrolled in any classes: \n")
    f.write(str([str(student.username) for student in registered_for_no_classes]))
    
    f.write("\n\n\n")
    for timeslot in timeslots:
        f.write("\n"+str(timeslot)+"\n\n\n")
        for section in sections:
            if section.get_meeting_times()[0] == timeslot:
                f.write(str(section)+": "+str(len(class_assignments[section]))+"/"+str(class_sizes[section])+"\n")
                f.write(str([str(student.username) for student in class_assignments[section]])+"\n\n")
    
    f.close()
    
    if save_enrollments:
        for section in class_assignments.keys():
            for student in class_assignments[section]:
                section.preregister_student(student)
    
        for sr in all_student_registrations:
            sr.end_date = NOW
            sr.save()
    
    return 0
    
if __name__ == "__main__":
    #Run as main program
    main()
