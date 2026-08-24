#!/usr/bin/env python2

from script_setup import *

PROGRAM_ID = 115

classes = ClassSubject.objects.filter(parent_program__id=115).exclude(status__in=[-20, -10])
num_total = classes.count()
num_approved = classes.filter(status__in=[5, 10]).count()
num_flag1 = ClassFlag.objects.filter(subject__parent_program__id=115, flag_type_id=4).distinct('subject').count()

print "%d Total Classes" % num_total
print "%d Approved" % num_approved
print "%d Approved by First Admin" % num_flag1
