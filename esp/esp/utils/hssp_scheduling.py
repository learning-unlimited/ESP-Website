#!/usr/bin/python
from esp.program.models import *
from esp.users.models import *

from collections import defaultdict
from datetime import datetime

def getClassesOfPriority(student, priority, program, timeblock):
    return ClassSection.objects.filter(meeting_times=timeblock).filter(anchor__userbit_qsc__user=student, anchor__userbit_qsc__qsc__parent__parent__parent=program.anchor, anchor__userbit_qsc__verb=GetNode("V/Flags/Registration/Priority/%d" % priority), anchor__userbit_qsc__startdate__lte=datetime.now(), anchor__userbit_qsc__enddate__gte=datetime.now()).distinct()

#def getClassesWithRank(student, score, program, timeblock):
#    return ClassSection.objects.filter(parent_class__parent_program=program).filter(parent_class__studentappquestion__studentapplication__user=student, parent_class__studentappquestion__studentapplication__reviews__score=score).distinct()

def getRankInClass(student, section):
    rank = max(list(StudentAppReview.objects.filter(studentapplication__user=student, studentapplication__program=section.parent_program, reviewer__in=section.teachers).values_list('score', flat=True)) + [-1])
    if rank == -1:
        rank = 10
    return rank

p = Program.objects.order_by('-id')[4]  # HSSP Spring 2010, as of this writing

print p

students = list(ESPUser(x) for x in p.students()['classreg'])
sections = list(p.sections().filter(status=10))
timeslots = list(p.getTimeSlots())

class_asgnments = defaultdict(list)
class_sizes = {}
for s in sections:
    class_sizes[s.id] = s.capacity - s.num_students()


#print students, sections, timeslots

for timeslot in timeslots:
    for stu in students:
        if stu.getEnrolledSections(p).filter(meeting_times=timeslot):
            stu.first_choice = []
            stu.second_choice = []
            stu.rank_in_first_choice = []
            stu.rank_in_second_choice = []
        else:
            stu.first_choice = getClassesOfPriority(stu, 1, p, timeslot).filter(status=10)
            stu.second_choice = getClassesOfPriority(stu, 2, p, timeslot).filter(status=10)
            stu.rank_in_first_choice = [getRankInClass(stu, fc) for fc in stu.first_choice]
            stu.rank_in_second_choice = [getRankInClass(stu, sc) for sc in stu.second_choice]

    for stu in students:
        if len(stu.first_choice) > 0:
            if stu.rank_in_first_choice[0] == 10:
                if len(class_asgnments[stu.first_choice[0].id]) < class_sizes[stu.first_choice[0].id]:
                    class_asgnments[ stu.first_choice[0].id ].append(stu)
                    stu.cls = stu.first_choice[0]
                    continue
        if len(stu.second_choice) > 0:
            if stu.rank_in_second_choice[0] == 10:
                if len(class_asgnments[stu.second_choice[0].id]) < class_sizes[stu.second_choice[0].id]:
                    class_asgnments[ stu.second_choice[0].id ].append(stu)
                    stu.cls = stu.second_choice[0]
                    continue
        if len(stu.first_choice) > 0:
            if stu.rank_in_first_choice[0] == 5:
                if len(class_asgnments[stu.first_choice[0].id]) < class_sizes[stu.first_choice[0].id]:
                    class_asgnments[ stu.first_choice[0].id ].append(stu)
                    stu.cls = stu.first_choice[0]
                    continue
                else:
                    print "%s  Couldn't assign student to first choice (as a 'Maybe') class because it was full: %s, %s  (trying second choice instead: %s, %s)" % (timeslot, stu, stu.first_choice, stu.second_choice, stu.rank_in_second_choice)
                    continue
        if len(stu.second_choice) > 0:
            if stu.rank_in_second_choice[0] == 5:
                if len(class_asgnments[stu.second_choice[0].id]) < class_sizes[stu.second_choice[0].id]:
                    class_asgnments[ stu.second_choice[0].id ].append(stu)
                    stu.cls = stu.second_choice[0]
                    continue
                else:
                    print "%s  Couldn't assign student to second choice (as a 'Maybe') class because it was full: %s, %s  (first choice: %s; rank %s)" % (timeslot, stu, stu.second_choice, stu.first_choice, stu.rank_in_first_choice)
                    continue

        if len(stu.first_choice) + len(stu.second_choice) == 0:
            pass # maybe print an error here?
        else:
            # We can only get here if we had an assignment fail
            if len([x for x in stu.rank_in_first_choice + stu.rank_in_second_choice if x != 1]) != 0:
                # Don't bother if they didn't apply for two classes
                if len(stu.first_choice) + len(stu.second_choice) >= 2:
                    print "%sam:  Failed to assign student %s to either their first or second choice classes: %s or %s (ratings %s and %s)" % (timeslot.start.hour, stu, [str(x) for x in stu.first_choice], [str(x) for x in stu.second_choice], stu.rank_in_first_choice, stu.rank_in_second_choice)

        
        
