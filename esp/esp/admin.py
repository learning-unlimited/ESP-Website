from __future__ import absolute_import
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

import logging

from esp.users.views import signout

from django.contrib.admin import ModelAdmin
from django.contrib.admin.sites import AdminSite
from django.core.exceptions import PermissionDenied
from django.views.decorators.cache import never_cache

#   Override the logout view on the admin site to use our own code
class ESPAdminSite(AdminSite):

    #   Log out using our view so that cookies are deleted correctly.
    @never_cache
    def logout(self, request, extra_context=None):
        return signout(request)

admin_site = ESPAdminSite()

logger = logging.getLogger(__name__)

#   A copy of Django's autodiscover function that accepts a site instance.
def autodiscover(site):
    from django.utils.module_loading import autodiscover_modules

    autodiscover_modules('admin', register_to=site)


class ReadOnlyModelAdmin(ModelAdmin):
    """ Lets admins look at rows but not add, change, or delete them.

    Django 1.11 has no view-only permission, so this shows every field as
    read-only, hides the save buttons, refuses any POST to the change form,
    and drops the actions menu (Django 1.11 lists "Delete selected" even
    without delete permission).
    """
    actions = None

    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields + self.model._meta.many_to_many]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def change_view(self, request, object_id, form_url='', extra_context=None):
        if request.method == 'POST':
            raise PermissionDenied('This model is read-only in the admin panel.')
        extra_context = dict(extra_context or {}, show_save=False, show_save_and_continue=False)
        return super(ReadOnlyModelAdmin, self).change_view(request, object_id, form_url, extra_context)


def register_remaining_models(site, excluded, read_only=()):
    """ Give every concrete model in ESP's own apps a default admin page,
    unless an admin.py already registered it or it's listed in excluded.
    Models listed in read_only get a ReadOnlyModelAdmin.  Both lists hold
    'app_label.ModelName' strings.  Returns the models registered here.

    Foreign keys to users that aren't AjaxForeignKeys get an ID box rather
    than a dropdown of every user.
    """
    from django.apps import apps
    from django.contrib.auth.models import User
    from django.db.models import ForeignKey
    from esp.db.fields import AjaxForeignKey

    excluded = set(label.lower() for label in excluded)
    read_only = set(label.lower() for label in read_only)
    models_by_label = dict((model._meta.label_lower, model) for model in apps.get_models())
    for setting, labels in (('ADMIN_PANEL_EXCLUDED_MODELS', excluded), ('ADMIN_PANEL_READ_ONLY_MODELS', read_only)):
        for label in labels - set(models_by_label):
            logger.warning('%s lists unknown model %s', setting, label)
    for label in read_only & set(models_by_label):
        if site.is_registered(models_by_label[label]):
            logger.warning('ADMIN_PANEL_READ_ONLY_MODELS lists %s, but its admin.py already registers it, '
                           'so that registration decides whether it is read-only', label)

    registered = []
    for model in apps.get_models():
        if (not model.__module__.startswith('esp.') or model._meta.proxy
                or site.is_registered(model) or model._meta.label_lower in excluded):
            continue
        user_fields = [field.name for field in model._meta.fields
                       if isinstance(field, ForeignKey) and not isinstance(field, AjaxForeignKey)
                       and issubclass(field.related_model, User)]
        base = ReadOnlyModelAdmin if model._meta.label_lower in read_only else ModelAdmin
        model_admin = type(str('%sDefaultAdmin' % model.__name__), (base,), {'raw_id_fields': user_fields})
        site.register(model, model_admin)
        registered.append(model)
    return registered

#   Properly add needed contrib modules to the Admin site
from django.contrib.sites.models import Site
admin_site.register(Site)

from django.contrib.redirects.models import Redirect
admin_site.register(Redirect)
