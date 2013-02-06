__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@lists.learningu.org
"""

import os

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), '..')

# Configure Django to support ESP
from django_settings import *

# Import system-specific settings
from local_settings import *

# Ensure database settings are set properly
if len(DATABASES['default']['USER']) == 0:
    try:
        DATABASES['default']['USER'] = DATABASE_USER
    except:
        raise Exception("You need to supply either DATABASES['default']['USER'] or DATABASE_USER in database_settings.py")
if len(DATABASES['default']['PASSWORD']) == 0:
    try:
        DATABASES['default']['PASSWORD'] = DATABASE_PASSWORD
    except:
        raise Exception("You need to supply either DATABASES['default']['PASSWORD'] or DATABASE_PASSWORD in database_settings.py")
if len(DATABASES['default']['NAME']) == 0:
    try:
        DATABASES['default']['NAME'] = DATABASE_NAME
    except:
        raise Exception("You need to supply either DATABASES['default']['NAME'] or DATABASE_NAME in local_settings.py")

SERVER_EMAIL = 'server@%s' % EMAIL_HOST_SENDER

############################################

# compute some derived settings
MEDIA_ROOT = os.path.join(PROJECT_ROOT, MEDIA_ROOT_DIR)
STATIC_ROOT = os.path.join(PROJECT_ROOT, STATIC_ROOT_DIR)

MANAGERS = ADMINS

TEMPLATE_DIRS = (
    os.path.join(PROJECT_ROOT, 'templates'),
)

DEFAULT_HOST = SITE_INFO[1]

for (key,value) in CONTACTFORM_EMAIL_CHOICES:
    if (key in ('esp','general','esp-web','relations')) and not (key in CONTACTFORM_EMAIL_ADDRESSES):
        CONTACTFORM_EMAIL_ADDRESSES[key] = DEFAULT_EMAIL_ADDRESSES[{'esp':'default','general':'default','esp-web':'support','relations':'default'}[key]]

#CACHE_BACKEND = "esp.utils.memcached_multikey://174.129.184.116:11211/?timeout=%d" % DEFAULT_CACHE_TIMEOUT
CACHE_BACKEND = "esp.utils.memcached_multikey://127.0.0.1:11211/?timeout=%d" % DEFAULT_CACHE_TIMEOUT

MIDDLEWARE_CLASSES = tuple([pair[1] for pair in sorted(MIDDLEWARE_GLOBAL + MIDDLEWARE_LOCAL)])

# set tempdir so that we don't have to worry about collision
import tempfile
import os
if not getattr(tempfile, 'alreadytwiddled', False): # Python appears to run this multiple times
    tempdir = os.path.join(tempfile.gettempdir(), "esptmp__" + CACHE_PREFIX)
    if not os.path.exists(tempdir):
        os.makedirs(tempdir)
    tempfile.tempdir = tempdir
    tempfile.alreadytwiddled = True
