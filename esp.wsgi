import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'

# Path for Django code
# sys.path.insert(0, '/lu/sites/stanford')
# Path for ESP code
sys.path.insert(0, '/lu/sites/stanford/esp')

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()




