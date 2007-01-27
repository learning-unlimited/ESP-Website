#!/usr/bin/python

import sys
sys.path += ['/esp/']
import operator
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

from esp.program.models import Program

if len(sys.argv) < 2:
    sys.exit()

programs = Program.objects.filter(id = sys.argv[1])
if len(programs) != 1:
    sys.exit()

program = programs[0]

students = reduce(operator.concat,[cls.students() for cls in program.classes()
                                   if not cls.isAccepted()                   ])

users = {}
for student in students:
    users[student.id] = student

for user in users.values():
    classes = ", ".join([ x.title() for x in
                          user.getEnrolledClasses().filter(parent_program = program)
                          if not x.isAccepted()                                       ])
    
    print '%s\t\t\t%s %s\t\t\t%s' % \
          (user.email, user.first_name, user.last_name, classes)




