import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

# Path for ESP code
sys.path.insert(0, '/home/ludev/devsite/esp')

import django.core.handlers.wsgi
django_application = django.core.handlers.wsgi.WSGIHandler()

USE_PROFILER = False

if USE_PROFILER:
    from repoze.profile.profiler import AccumulatingProfileMiddleware
    application = AccumulatingProfileMiddleware(
      django_application,
      log_filename='/tmp/djangoprofile.log',
      discard_first_request=True,
      flush_at_shutdown=True,
      path='/__profile__')
else:
    application = django_application

