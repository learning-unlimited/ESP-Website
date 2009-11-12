#!/usr/bin/python

from esp.users.models import ESPUser

user_set = ESPUser.objects.filter(userbit__verb__name='Teacher')
for u in user_set:
    u.convertAvailability()
    print 'Converted availability for %s' % u.name()
