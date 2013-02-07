from esp.program.models import Program, StudentRegistration, ClassSection
from esp.users.models import ESPUser
from esp.users.models.userbits import UserBit
from esp.datatree.models import GetNode
from datetime import datetime, timedelta, date, time
from django.db.models.aggregates import Min

# Splash 2012
prog = Program.objects.get(id=85)
# classes that started more than 120 minutes ago
passed_sections = prog.sections().annotate(begin_time=Min("meeting_times__start")).filter(status=10, parent_class__status=10, begin_time__start__lt=datetime.now() - timedelta(minutes=120), begin_time__start__gt = datetime.combine(date.today(), time(0, 0)))
# students who are enrolled in a class that started more than 120 minutes ago, who have not checked in
#students = ESPUser.objects.filter(studentregistration__in=StudentRegistration.valid_objects(), studentregistration__relationship=1, studentregistration__section__in=passed_sections).distinct().exclude(userbit__in=UserBit.valid_objects(), userbit__qsc=prog.anchor, userbit__verb=GetNode('V/Flags/Registration/Attended'))
all_students = ESPUser.objects.filter(studentregistration__in=StudentRegistration.valid_objects(), studentregistration__relationship=1, studentregistration__section__in=passed_sections).distinct()
students = set(all_students) - set(all_students.filter(userbit__in=UserBit.valid_objects(), userbit__qsc=prog.anchor, userbit__verb=GetNode('V/Flags/Registration/Attended')))
# classes that start today
upcoming_sections = prog.sections().annotate(begin_time=Min("meeting_times__start")).filter(status=10, parent_class__status=10, begin_time__start__gt=datetime.now(), begin_time__start__lt=datetime.combine(date.today(), time(23, 59)))
# registrations of missing students for upcoming classes
registrations = StudentRegistration.valid_objects().filter(user__in=students, section__in=upcoming_sections, relationship=1)
# filter out materials-intensive classes
registrations = registrations.exclude(section__parent_class__id__in=[6090, 6141, 6781, 6782, 6783, 6698, 6160, 6163, 6196, 6787, 6793, 6337, 6191, 6200, 6217, 6240, 6282, 6340, 6343, 6393, 6272, 6279, 6203, 6278, 6322, 6358, 6317, 6406, 6419, 6418, 6428, 6400, 6450, 6411, 6459, 6470, 6674, 6521, 6675, 6703, 6681, 6329, 6491, 6554, 6509, 6535, 6578, 6524, 6204, 6542, 6326, 6599, 6686, 6625, 6633, 6634, 6641, 6255, 6649, 6799, 6661, 6695, 6730, 6199, 6390, 6299, 6466, 6253, 6144])
registrations.update(end_date=datetime.now())
print list(registrations)
