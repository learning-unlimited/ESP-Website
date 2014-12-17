from esp.program.models import *

splash = Program.objects.get(id=2)

students = [ESPUser(x) for x in splash.students()['attended']]

school_dict = {}

for student in students:
    school = student.getLastProfile().student_info.school
    if school is None or len(school) == 0:
        school = 'N/A'
    print student.id, student.first_name, student.last_name, school
    if school not in school_dict:
        school_dict[school] = []
    school_dict[school].append(student)

schools = school_dict.keys()
def school_key(school):
    if isinstance(school, basestring):
        return school.lower()
    else:
        return 'N/A'

schools.sort(key=school_key)

for school in schools:
    print '%s: %d students' % (school, len(school_dict[school]))
    for student in school_dict[school]:
        print '  %s %s (%d) %s' % (student.first_name, student.last_name, student.id, student.email)

