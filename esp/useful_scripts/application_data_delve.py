from esp.program.models import Program, StudentRegistration, ClassSection
from esp.program.models.app_ import StudentApplication, StudentAppResponse, StudentAppReview
from esp.users.models import ESPUser
from django.db.models.aggregates import Count
import datetime
import csv
import os

def getRankInClass(student, section):
    if StudentRegistration.objects.filter(section=section, relationship__name="Rejected",end_date__gte=datetime.datetime.now(),user=student).count() or not student.studentapplication_set.filter(program = section.parent_class.parent_program).count() or not StudentAppResponse.objects.filter(question__subject=section.parent_class, studentapplication__user=student).count():
        return 1
    for sar in StudentAppResponse.objects.filter(question__subject=section.parent_class, studentapplication__user=student):
        if not len(sar.response.strip()):
            return 1
    rank = max(list(StudentAppReview.objects.filter(studentapplication__user=student, studentapplication__program=section.parent_program, reviewer__in=section.teachers).values_list('score', flat=True)) + [-1])
    return rank

program = Program.objects.get(id=82)
deadline = datetime.datetime(2012,6,2)
filename = 'DelveApplicantsRetry.csv'

all_studentreg_data = StudentRegistration.objects.filter(section__parent_class__parent_program=program,end_date__gt=datetime.datetime.now(),start_date__lt=deadline,relationship__name__contains="Priority/").distinct().order_by('user','relationship__name').distinct().values('user','user__username','user__last_name','user__first_name','user__email','section','section__parent_class','section__parent_class__anchor__friendly_name','start_date','relationship__name').distinct().order_by('user','relationship__name').distinct()

all_student_apps = StudentApplication.objects.filter(program=program).distinct().annotate(num_responses=Count('responses')).distinct().order_by('-num_responses').distinct()

f = csv.DictWriter(open(os.getenv("HOME")+'/'+filename, 'wb'), ['user','user__username','user__last_name','user__first_name','user__email','section','section__parent_class','section__parent_class__anchor__friendly_name','relationship__name','start_date','response','rank'])
f.writerow({'user':'User ID#','user__username':'Username','user__last_name':'Last Name','user__first_name':'First Name','section':'Section ID#','section__parent_class':'Class ID#','section__parent_class__anchor__friendly_name':'Class Name','relationship__name':'Priority','start_date':'Time Applied','response':'Student Application Response','rank':'Score'})

for r in all_studentreg_data:
    d = dict(r)
    d['response'] = all_student_apps.filter(user=d['user']).distinct()[0].responses.filter(question__subject=d['section__parent_class'])[0].response
    d['rank'] = getRankInClass(ESPUser.objects.get(id=d['user']),ClassSection.objects.get(id=d['section']))
    for k in d.keys():
        if isinstance(d[k],basestring):
            d[k]=d[k].encode('ascii','ignore')
    f.writerow(d)
