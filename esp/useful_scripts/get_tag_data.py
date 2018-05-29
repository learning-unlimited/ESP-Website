"""Script to get tags the site has set as JSON for later processing."""

from script_setup import *

import json
from django.conf import settings

domain = settings.SITE_INFO[1].split('.')
if domain[0] == 'www':
    short_domain = domain[1]
else:
    short_domain = domain[0]

with open('/home/benkraft/tags_%s.json' % short_domain, 'w') as f:
    json.dump([{'key': t.key, 'value': t.value, 'target': str(t.target)}
               for t in Tag.objects.all()],
              f, indent=4)
