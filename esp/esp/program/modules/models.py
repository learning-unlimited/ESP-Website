
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


# Fields that are always kept in sync with code on every install().
# These are NOT customizable by chapters.
ALWAYS_UPDATE_FIELDS = {'admin_title', 'inline_template', 'choosable'}

# Fields where NULL in the database means "use the code default from
# module_properties()".  A non-NULL value means a chapter has explicitly
# customized the field and install() will not overwrite it.
CUSTOMIZABLE_FIELDS = {'link_title', 'seq', 'required'}


def updateModules(update_data, overwriteExisting=False, deleteExtra=False, model=None):  # noqa: N803 (overwriteExisting kept for backward compat)
    """
    Given a list of key:value dictionaries containing fields from the
    ProgramModule table, populate the table based on that list.

    For existing modules:
      - Always updates ALWAYS_UPDATE_FIELDS (admin_title, inline_template,
        choosable) from code so that developer changes propagate.
      - Never touches CUSTOMIZABLE_FIELDS (link_title, seq, required);
        NULL means "use code default", non-NULL means "chapter override".

    For new modules:
      - Creates the record with CUSTOMIZABLE_FIELDS set to NULL so they
        automatically track code defaults.
      - Populates all other fields from the provided data.

    If deleteExtra is set, entries in the table that don't correspond
    to modules in the list will be deleted.
    """
    from esp.program.models import ProgramModule

    if model is None:
        model = ProgramModule

    #   Select existing modules only by handler and module type, which are assumed to be unique.
    mods = []
    for datum in update_data:
        query_kwargs = {'handler': datum["handler"], 'module_type': datum["module_type"]}
        mod = model.objects.filter(**query_kwargs).first()
        if mod is not None:
            # Always update non-customizable fields from code
            changed = False
            for field in ALWAYS_UPDATE_FIELDS:
                if field in datum and getattr(mod, field) != datum[field]:
                    setattr(mod, field, datum[field])
                    changed = True
            if changed:
                mod.save()
            mods.append((datum, (mod, False)))
        else:
            # Clean up non-DB keys before creating
            for key in ('main_call', 'aux_calls'):
                datum.pop(key, None)
            # Build defaults dict: populate identity + always-update fields,
            # leave customizable fields as NULL (code default).
            new_defaults = {k: v for k, v in datum.items()
                           if k not in CUSTOMIZABLE_FIELDS}
            query_kwargs['defaults'] = new_defaults
            mods.append((datum, model.objects.get_or_create(**query_kwargs)))

    if deleteExtra:
        ids = [mod.id for (datum, (mod, created)) in mods]
        ProgramModule.objects.exclude(id__in=ids).delete()

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
