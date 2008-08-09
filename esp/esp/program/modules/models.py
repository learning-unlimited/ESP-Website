
__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""

from esp.program.modules.handlers import *

def updateModules(update_data, overwriteExisting=False, deleteExtra=False):
    """
    Given a list of key:value dictionaries containing fields from the
    ProgramModule table, populate the table based on that list.
    If overwriteExisting is set, modules that already have entries will
    be updated with the specified data.
    If deleteExtra is set, entries in the table that don't correspond
    to modules in the list will be deleted.
    """
    from esp.program.models import ProgramModule
    
    mods = [ (datum, ProgramModule.objects.get_or_create(handler=datum["handler"], module_type=datum["module_type"], defaults=datum)) for datum in update_data ]

    if overwriteExisting:
        for (datum, (mod, created)) in mods:
            if created:
                mod.__dict__.update(datum)
                mod.save()

    if deleteExtra:
        ids = []

        for (datum, (mod, created)) in mods:
            ids.append(mod.id)

        ProgramModule.objects.exclude(id__in=ids).delete()

    
def install():
    """ Install the initial ProgramModule table data for all currently-existing modules """
    print "Installing esp.program.modules initial data..."
    from esp.program.modules import handlers
    modules = [ x for x in handlers.__dict__.values() if hasattr(x, "module_properties") ]

    table_data = []
    for module in modules:
        table_data += module.module_properties_autopopulated()

    updateModules(table_data)
    
