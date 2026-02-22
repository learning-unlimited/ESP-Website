__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2012 by the individual contributors
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

from esp.users.views import signout

from django.contrib.admin.sites import AdminSite
from django.views.decorators.cache import never_cache

#   Override the logout view on the admin site to use our own code
class ESPAdminSite(AdminSite):

    #   Log out using our view so that cookies are deleted correctly.
    @never_cache
    def logout(self, request, extra_context=None):
        return signout(request)

admin_site = ESPAdminSite()

#   A copy of Django's autodiscover function that accepts a site instance.
def autodiscover(site):
    from django.utils.module_loading import autodiscover_modules

    autodiscover_modules('admin', register_to=site)

#   Properly add needed contrib modules to the Admin site
from django.contrib.sites.models import Site
admin_site.register(Site)

from django.contrib.redirects.models import Redirect
admin_site.register(Redirect)
