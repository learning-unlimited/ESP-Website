from script_setup import *
import re

def purify(s):
    return re.sub(r'\W+', '', s, flags=re.UNICODE)

prog = Program.objects.get(name='Splash 2016')
enrollments = StudentRegistration.valid_objects().filter(
    section__parent_class__parent_program=prog,
    relationship__name='Enrolled')

names = list(sorted(purify(name.upper()) for (name, _) in enrollments.values_list('user__last_name', 'user').distinct()))
print(names)
print(len(names))
m = len(names)//18
print(m)
print(names[::m])
print(' '.join(sorted(set(name[:2] for name in names))))
