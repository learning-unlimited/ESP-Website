from __future__ import with_statement

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

from django.db.models import signals, get_apps, get_models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.management import update_contenttypes
from esp.web import models as web
from esp.utils.custom_cache import custom_cache

def update_esp_contenttypes(app_config, content_type_class=ContentType, verbosity=2, **kwargs):
    """
    Removes any content type model entries in the given app that no longer have
    a matching model class, then creates content types.

    django.contrib.contenttypes.management.update_contenttypes() does this,
    except it requires interactive raw input from the command line in order to
    remove stale content types. So this function copies the deletion
    functionality without the interactivity, and then calls the function.
    See <https://github.com/django/django/blob/30eb916bdb9b6b9fc881dfda919b49d036953a3b/django/contrib/contenttypes/management.py>.

    The content_type_class defaults to ContentType, but allows a frozen ORM to
    be passed in for use during a migration.

    Re-copied for Django 1.8 updates
    """
    if not app_config.models_module:
        return

    try:
        ContentType = apps.get_model('contenttypes', 'ContentType')
    except LookupError:
        return

    if not router.allow_migrate_model(using, ContentType):
        return

    ContentType.objects.clear_cache()

    app_label = app_config.label

    app_models = {
        model._meta.model_name: model
        for model in app_config.get_models()}

    if not app_models:
        return

    # Get all the content types
    content_types = {
        ct.model: ct
        for ct in ContentType.objects.using(using).filter(app_label=app_label)
    }
    to_remove = [
        ct
        for (model_name, ct) in six.iteritems(content_types)
        if model_name not in app_models
    ]

    if to_remove:
        for ct in to_remove:
            if verbosity >= 2:
                print("Deleting stale content type '%s | %s'" % (ct.app_label, ct.model))
            ct.delete()

    update_contenttypes(app, verbosity, interactive=False, **kwargs)

def update_all_esp_contenttypes(content_type_class=ContentType, verbosity=2, **kwargs):
    for app in get_apps():
        update_esp_contenttypes(app, None, content_type_class, verbosity, **kwargs)

signals.post_migrate.connect(update_esp_contenttypes)

