import Program
from esp.program.models import Program
from esp.users.models import ESPUser
from esp.datetime import datetime

splash = Program.objects.get(id = 65)
splash_teachers = splash.teachers['class_approved']

allclasses = prog.sections().filter(status=10, parent_class__status=10, meeting_times__isnull=False)
first_timeblock_dict = allclasses.aggregate(Min('meeting_times__start'))

first_class_times_saturday = dict()
first_class_times_sunday = dict()

far_future = datetime(2011, 3, 4, 21, 8, 12)


for teacher in splash_teacher:
    teacher = ESPUser(teacher)
    sections = teacher.getTaughtSectionsFromProgram(splash)
    first_saturday = far_future
    first_sunday = far_future
    for section in sections:
        starttime = section.meeting_times.all().order_by('start')[0]
        if starttime.date == 20:
            if starttime < first_saturday:
                first_sarturday = starttime
        else:
            if starttime < first_sunday:
                first_sunday = starttime

        ci = ContactInfo.objects.filter(user=teacher, phone_cell__isnull=False).exclude(phone_cell='').order_by('id')
        if ci.count() > 0:
                phone_day = ci[0].phone_day
                phone_cell = ci[0].phone_cell
                phone_day = ci[0].phone_day
        else:
                phone_day = 'N/A'
                phone_cell = 'N/A'


    if not first_class_times_saturday[__str__(starttime)]:
        first_class_times_saturday[__str__(starttime)] = []
    first_class_times_saturday[__str__(starttime)].append(teacher.first_name + ' ' + teacher.last_name + ': ' + phone_cell + '\n')

    if not first_class_times_sunday[__str__(starttime)]:
        first_class_times_sunday[__str__(starttime)] = []
    first_class_times_sunday[__str__(starttime)].append(teacher.first_name + ' ' + teacher.last_name + ': ' + phone_cell + '\n')

print 'Saturday\n'
print first_class_times_saturday
print 'Sunday\n'
print first_class_times_sunday
