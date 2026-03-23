__author__ = "Individual contributors (see AUTHORS file)"
__date__ = "$DATE$"
__rev__ = "$REV$"
__license__ = "AGPL v.3"
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

from django.contrib.admin.sites import AdminSite
from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site
from django.utils.module_loading import autodiscover_modules
from django.views.decorators.cache import never_cache

from esp.users.views import signout


class ESPAdminSite(AdminSite):
    """
    Custom AdminSite for ESP project.

    Overrides the default logout behavior to use the project's
    custom signout view.
    """

    @never_cache
    def logout(self, request, extra_context=None):
        """
        Log out using custom signout view to ensure cookies are cleared properly.
        """
        return signout(request)


# Instantiate custom admin site
admin_site = ESPAdminSite()


def autodiscover(site):
    """
    Discover admin modules and register them to the provided site instance.

    This is a wrapper around Django's autodiscover_modules that allows
    passing a custom admin site instance.
    """
    autodiscover_modules("admin", register_to=site)


# Register default Django models with custom admin site
admin_site.register(Site)
admin_site.register(Redirect)
