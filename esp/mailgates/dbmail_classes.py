#!/usr/bin/python

import sys
sys.path += ['/esp/']

import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

from esp.program.models import Class

if len(sys.argv) < 3:
    sys.exit()

classes = Class.objects.filter(id = sys.argv[1])
if len(classes) != 1:
    sys.exit()

clsobj = classes[0]

request = sys.argv[2]
if request == 'class':
    users = list(clsobj.teachers()) + clsobj.students()
elif request == 'students':
    users = clsobj.students()
elif request == 'teachers':
    users = list(clsobj.teachers())

for user in users:
    print '%s\t\t\t%s %s' % \
          (user.email, user.first_name, user.last_name)




