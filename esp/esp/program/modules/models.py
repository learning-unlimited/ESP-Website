
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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
logger = logging.getLogger(__name__)

from esp.program.modules.handlers import * # Needed for app loading, don't delete
from django.db.models import Q

def updateModules(update_data, overwriteExisting=False, deleteExtra=False, model=None):
    """
    Given a list of key:value dictionaries containing fields from the
    ProgramModule table, populate the table based on that list.
    If overwriteExisting is set, modules that already have entries will
    be updated with the specified data.
    If deleteExtra is set, entries in the table that don't correspond
    to modules in the list will be deleted.
    """
    from esp.program.models import ProgramModule

    if model is None:
        model = ProgramModule

    #   Select existing modules only by handler and module type, which are assumed to be unique.
    mods = []
    global_defaults = {'seq': 0, 'required': False}
    for datum in update_data:
        query_kwargs = {'handler': datum["handler"], 'module_type': datum["module_type"]}
        qs = model.objects.filter(**query_kwargs)
        if qs.exists():
            mods.append((datum, (qs[0], False)))
        else:
            if 'main_call' in datum:
                datum.pop('main_call')
            if 'aux_calls' in datum:
                datum.pop('aux_calls')
            #   Ensure that all of the required fields are present when calling get_or_create
            new_obj_defaults = global_defaults.copy()
            new_obj_defaults.update(datum)
            query_kwargs['defaults'] = new_obj_defaults

            mods.append((datum, model.objects.get_or_create(**query_kwargs)))

    if overwriteExisting:
        for (datum, (mod, created)) in mods:
            if not created:
                mod.__dict__.update(datum)
                mod.save()

    if deleteExtra:
        ids = []

        for (datum, (mod, created)) in mods:
            ids.append(mod.id)

        ProgramModule.objects.exclude(id__in=ids).delete()

    for (datum, (mod, created)) in mods:
        #   If the module exists but the provided data adds fields that
        #   are null or blank, go ahead and add them.
        #   This simplifies data migrations where the default module properties
        #   are changed.
        for key in datum:
            if (key not in mod.__dict__) or (mod.__dict__[key] is None) or (mod.__dict__[key] == ''):
                if datum[key] is not None and datum[key] != u'':
                    mod.__dict__[key] = datum[key]

        mod.save()

def install(model=None):
    """ Install the initial ProgramModule table data for all currently-existing modules """
    logger.info("Installing esp.program.modules initial data...")
    from esp.program.modules import handlers
    modules = [ x for x in handlers.__dict__.values() if hasattr(x, "module_properties") ]

    table_data = []
    for module in modules:
        table_data += module.module_properties_autopopulated()

    updateModules(table_data, deleteExtra=True, model=model)

from esp.program.modules.module_ext import *
