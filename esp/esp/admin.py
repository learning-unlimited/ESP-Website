__author__ = "Individual contributors (see AUTHORS file)"
__date__ = "$DATE$"
__rev__ = "$REV$"
__license__ = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
...
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
