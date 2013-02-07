from esp.program.models import Program, StudentRegistration, ClassSection
from esp.program.models.app_ import StudentApplication, StudentAppResponse, StudentAppReview
from esp.users.models import ESPUser
from django.db.models.aggregates import Count
import datetime
import csv
import os

program = Program.objects.get(id=82)
deadline = datetime.datetime.now()

def getRanksInClass(student, section):
    if StudentRegistration.objects.filter(section=section, relationship__name="Rejected",end_date__gte=datetime.datetime.now(),user=student).count():
        return "1 (Has a Rejected StudentRegistration for this section)"
    if not student.studentapplication_set.filter(program = section.parent_class.parent_program).count():
        return "1 (Has no StudentApplications for this program)"
    if not StudentAppResponse.objects.filter(question__subject=section.parent_class, studentapplication__user=student).count():
        return "1 (Has no StudentAppResponses for this section)"
    for sar in StudentAppResponse.objects.filter(question__subject=section.parent_class, studentapplication__user=student):
        if not len(sar.response.strip()):
            return "1 (Has a StudentAppResponse for this section which is empty)"
    ranks = list(StudentAppReview.objects.filter(studentapplication__user=student, studentapplication__program=section.parent_program, reviewer__in=section.teachers).values('reviewer__username','score'))
    if len(ranks):
        return "\n".join(map(lambda d: "%(reviewer__username)s: %(score)s" % d, ranks))
    else:
        return "-1 (No StudentAppReviews)"

values = ['user','user__username','user__last_name','user__first_name','user__email','section','section__parent_class','section__parent_class__anchor__friendly_name','start_date','relationship__name']
all_studentreg_data = StudentRegistration.objects.filter(section__parent_class__parent_program=program,end_date__gt=datetime.datetime.now(),start_date__lt=deadline,relationship__name__contains="Priority/",user__studentapplication__program=program,section__parent_class__studentappquestion__studentappresponse__isnull=False).distinct().order_by('user','relationship__name').distinct().values(*values).distinct().order_by('user','relationship__name').distinct()

all_student_apps = StudentApplication.objects.filter(program=program).distinct().annotate(num_responses=Count('responses')).distinct().order_by('-num_responses').distinct()

f = csv.DictWriter(open(os.getenv("HOME")+'/'+program.niceName().replace(" ","_")+'Applicants.csv', 'wb'), ['user','user__username','user__last_name','user__first_name','user__email','section','section__parent_class','section__parent_class__anchor__friendly_name','relationship__name','start_date','response','ranks'])
f.writerow({'user':'User ID#','user__username':'Username','user__last_name':'Last Name','user__first_name':'First Name','section':'Section ID#','section__parent_class':'Class ID#','section__parent_class__anchor__friendly_name':'Class Name','relationship__name':'Priority','start_date':'Time Applied','response':'Student Application Response','ranks':'Scores'})

for r in all_studentreg_data:
    d = dict(r)
    d['ranks'] = getRanksInClass(ESPUser.objects.get(id=d['user']),ClassSection.objects.get(id=d['section']))
    try:
        d['response'] = all_student_apps.filter(user=d['user']).distinct()[0].responses.filter(question__subject=d['section__parent_class'])[0].response
    except Exception:
        print "FAILED AT\n", str(d), "\n\n\n"
    for k in d.keys():
        if isinstance(d[k],basestring):
            d[k]=d[k].encode('ascii','ignore')
    f.writerow(d)
