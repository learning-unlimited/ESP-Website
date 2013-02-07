import datetime
from django.db.models.aggregates import Sum
from esp.program.models import Program,StudentRegistration
from esp.program.models.class_ import ClassSection, ClassSubject, open_class_category
from esp.users.models import ESPUser

program = Program.objects.get(id=75)
students = ESPUser.objects.filter(studentregistration__section__parent_class__parent_program=program,studentregistration__end_date__gt=datetime.datetime.now(),studentregistration__relationship__name__in=["Priority/1","Interested"]).distinct()
f = open('/home/jmoldow/SparkPhase1-2.csv','w')
f.write('"Student (username)","High School Graduation Year","Grade","# of Priority/1 Classes","# of Priority/1 Class Enrollments after Phases 1&2","Total Duration of Priority/1 Classes","Total Duration of Priority/1 Enrolled Classes after Phases 1&2"\n')
BOUND = 17
enrollments = [0 for i in range(BOUND)]
flagged_classes = [0 for i in range(BOUND)]
enrollments_and_flagged_classes = [[0 for i in range(BOUND)] for j in range(BOUND)]
for student in students:
    graduation_year = student.studentinfo_set.order_by('-id')[0].graduation_year
    grade = student.getGrade(program=program)
    sr_request = StudentRegistration.objects.filter(user=student,section__parent_class__parent_program=program,relationship__name="Priority/1",end_date__gt=datetime.datetime.now()).distinct()
    sr_request_count = sr_request.count()
    sr_requested_classes = sr_request.values_list('section',flat=True).distinct()
    sr_enrolled = StudentRegistration.objects.filter(user=student,section__id__in=sr_requested_classes,relationship__name="Enrolled",end_date__gt=datetime.datetime.now()).distinct()
    sr_enrolled_count = sr_enrolled.count()
    enrollments[sr_enrolled_count] += 1
    flagged_classes[sr_request_count] += 1
    enrollments_and_flagged_classes[sr_enrolled_count][sr_request_count] += 1
    sr_enrolled_classes = sr_enrolled.values_list('section',flat=True).distinct()
    sr_enrolled_classes = ClassSection.objects.filter(id__in=sr_enrolled_classes)
    sr_requested_classes = ClassSection.objects.filter(id__in=sr_requested_classes).distinct()
    from django.db.models.aggregates import Sum
    enrolled_dur = sr_enrolled_classes.aggregate(enrolled_dur=Sum('duration'))['enrolled_dur']
    requested_dur = sr_requested_classes.aggregate(requested_dur=Sum('duration'))['requested_dur']
    f.write('"%s",%s,%s,%s,%s,%s,%s\n' % (student,graduation_year,grade,sr_request_count,sr_enrolled_count,requested_dur,enrolled_dur))
f.close()
f = open('/home/jmoldow/SparkPhase1-2.txt','w')
for i in range(BOUND):
    f.write('Number of Students Enrolled in %s Priority/1 Classes after Phases 1 and 2: %s\n' % (i, enrollments[i]))
f.write('\n\n')
for i in range(BOUND):
    f.write('Number of Students Who Flagged %s Priority/1 Classes: %s\n' % (i, flagged_classes[i]))
f.close()
f = open('/home/jmoldow/SparkPhase1-2-grid.csv','w')
f.write('"Horizontal Axis: Number of Flagged Priority/1 Classes",\n"Vertical Axis: Number of Enrolled Priority/1 Classes after Phases 1 and 2",\n')
f.write(',%s\n' % ','.join([str(i) for i in range(BOUND)]))
for i in range(BOUND):
    f.write('%s,%s\n' % (i, ','.join(map(str,enrollments_and_flagged_classes[i]))))
f.close()
import csv
f = csv.writer(open('/home/jmoldow/SparkPhase1-2-sections.csv','wb'))
f.writerow(["Section","# of Priority/1 Students","# of Priority/1 Enrolled Students after Phases 1 and 2","Section Capacity","Percent Full","Popularity ((# priority/1 students)/(capacity))"])
for subject in ClassSubject.objects.catalog(program):
    if subject.category == open_class_category():
        continue
    for section in subject.sections.all():
        priorities = ESPUser.objects.filter(studentregistration__section=section,studentregistration__relationship__name="Priority/1",studentregistration__end_date__gt=datetime.datetime.now()).distinct().count()
        enrolled = ESPUser.objects.filter(studentregistration__section=section,studentregistration__relationship__name="Enrolled",studentregistration__end_date__gt=datetime.datetime.now()).distinct().count()
        capacity = section.capacity
        percent_full = float(enrolled)/float(capacity)
        popularity = float(priorities)/float(capacity)
        f.writerow(map(unicode,[section, priorities, enrolled, capacity, percent_full, popularity]))








