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

from django.contrib.admin.options import ModelAdmin
from django.contrib.admin.sites import AdminSite
from django.contrib.redirects.models import Redirect
from django.contrib.sites.models import Site
from django.utils.decorators import method_decorator
from django.utils.module_loading import autodiscover_modules
from django.views.decorators.cache import never_cache

from esp.users.views import signout


def sets_save_as(admin_class):
    """
    Whether admin_class picks its own value for `save_as`.

    Django's own ModelAdmin always defines `save_as`, so the search stops
    there; only a value set by one of our classes counts as a choice.
    """
    for klass in getattr(admin_class, '__mro__', ()):
        if klass is ModelAdmin:
            break
        if 'save_as' in vars(klass):
            return True
    return False


class ESPAdminSite(AdminSite):
    """
    Custom AdminSite for ESP project.

    Overrides the default logout behavior to use the project's
    custom signout view, and turns on Django's "Save as new" button so that
    objects can be duplicated from their change page.
    """

    @method_decorator(never_cache)
    def logout(self, request, extra_context=None):
        """
        Log out using custom signout view to ensure cookies are cleared properly.
        """
        return signout(request)

    def register(self, model_or_iterable, admin_class=None, **options):
        """
        Register model(s), enabling "Save as new" unless the admin opts out.

        Duplicating an object is useful for most of what we keep in the admin
        panel, so it is the default here rather than something every
        ModelAdmin has to remember to turn on.  Two kinds of admin set
        `save_as = False` for themselves: those whose add form cannot produce
        a saveable duplicate (a required field is readonly, excluded, or
        `editable=False`), and those for records of something that already
        happened, where a hand-made copy would be fabricated history.
        """
        if 'save_as' not in options and not sets_save_as(admin_class):
            options['save_as'] = True
        super().register(model_or_iterable, admin_class, **options)


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
