""" The middleware to implement the queue. """

import time
from esp.queue.models import *
from django.http import HttpResponse
from django.core.cache import cache
from datetime import datetime, timedelta
import os
import re
import random

no_queue_list = [
    r'^18.187.',
    r'^18.208.',
    ]

no_queue_list = [ re.compile(x) for x in no_queue_list ]

USERS_IN_SITE = 150
SITE_TIMEOUT = timedelta(minutes=5)
SITE_REFRESH_TIME = 240
CACHE_KEY_USERS = "CACHE_KEY_USERS_ON_SITE"
CACHE_KEY_IN = "CACHE_KEY_USERS_IN_SITE"

class QueueMiddleware(object):

    def process_request(self, request):
        if os.getloadavg()[1] < 10.0: # We don't care for less-than-crazy loads
            return None

        ip = request.META['REMOTE_ADDR']
        for i in no_queue_list:
            if re.search(i, ip):
                return None

        do_clean = random.randint(0, USERS_IN_SITE)
        if do_clean == 0:
            UserQueue.objects.filter(time_since_last_refresh__lte = datetime.now()-SITE_TIMEOUT).delete()

        browser_key = ip + ':' + request.META.get('HTTP_USER_AGENT','')
        browser_key = browser_key[:60]

        queueentry, created = UserQueue.objects.get_or_create(browser = browser_key)

        if queueentry.in_site:
            return None

        in_site_users_count = cache.get(CACHE_KEY_IN)
        if in_site_users_count == None:
            in_site_users_count = UserQueue.objects.filter(in_site=True).count()
            cache.set(CACHE_KEY_IN, in_site_users_count, 2)

        if in_site_users_count < USERS_IN_SITE:
            cache.set(CACHE_KEY_IN, in_site_users_count + 1)
            queueentry.in_site = True
            queueentry.save()
            return None

        if not created:
            queueentry.save()

        users_on_site = cache.get(CACHE_KEY_USERS)
        if users_on_site == None:
            users_on_site = UserQueue.objects.filter(in_site=False).count()
            cache.set(CACHE_KEY_USERS, users_on_site, SITE_REFRESH_TIME)
        elif created:
            users_on_site = users_on_site + 1
            cache.set(CACHE_KEY_USERS, users_on_site, SITE_REFRESH_TIME)


        message = """
<h1>Please wait...</h1>

<p>Our server is under extreme load. To satisfy everyone's need, you
have been placed in a queue. You are in a line of %s people.
<br /><br />
<!-- Your estimated time is: <strong>TODO</strong> //-->

<strong>Note: Please do not refresh and/or close this page! This
page will automatically reload and update for you.</strong>
""" % (users_on_site)

        page = open(QUEUE_FILE, 'r').read(50000) % message

        response = HttpResponse(page)
        response['Refresh'] = str(SITE_REFRESH_TIME)

        return response
