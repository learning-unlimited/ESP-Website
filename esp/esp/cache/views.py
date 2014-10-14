
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 by the individual contributors
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
  Email: web-team@learningu.org
"""

from esp.cache.registry import all_caches
from esp.users.models import admin_required, ESPUser
from esp.web.util.main import render_to_response
from esp.cache.varnish import purge_page
from django.http import HttpResponse

@admin_required
def view_all(request):
    caches = sorted(all_caches.values(), key=lambda c: c.name)
    cache_data = [{'pretty_name': cache.pretty_name, 'hit_count': cache.hit_count, 'miss_count': cache.miss_count} for cache in caches]
    return render_to_response('cache/view_all.html', request, {'caches': cache_data})

def varnish_purge(request):
    # Authenticate
    if (not request.user or not request.user.is_authenticated() or not ESPUser(request.user).isAdministrator()):
        raise PermissionDenied
    # Purge the page specified
    purge_page(request.POST['page'])
    # Return the minimum possible
    return HttpResponse('')
