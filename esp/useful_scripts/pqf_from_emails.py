#!/usr/bin/env python

from esp.users.models import User, ESPUser, PersistentQueryFilter
from django.db.models.query import Q

url = 'http://splashchicago.learningu.org/manage/Splash/2010_Fall/maincomm'
filename = '/home/pricem/past_students.txt'

file = open(filename)
data = file.readlines()
file.close()

addr_list = []
for line in data:
    addr_list.append(line.strip())
print 'Read %d addresses' % len(addr_list)

addr_list = list(set(addr_list))
print 'Found %d distinct addresses' % len(addr_list)

idmap = {}
users = ESPUser.objects.filter(email__in=addr_list).order_by('-id')
for u in users:
    if u.email not in idmap:
        idmap[u.email] = u.id

id_list = idmap.values()

user_q = Q(id__in=id_list)
pqf = PersistentQueryFilter.create_from_Q(User, user_q, 'Custom list generated from email addresses')

print 'Found %d users' % ESPUser.objects.filter(user_q).distinct().count()

print 'Created filter.  Edit and send your email at: %s' % ("""
%s?extra=%d&op=usersearch&userid=&username=&last_name=&first_name=&email=&zipdistance_exclude=&zipdistance=&zipcode=02139&states=&grade_min=7&grade_max=13&submitform=Use+Filtered+List""" % (url, pqf.id))

