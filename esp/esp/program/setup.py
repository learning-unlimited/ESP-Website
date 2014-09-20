
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
from esp.datatree.models import *
from esp.users.models import ESPUser, User, Permission
from esp.program.Lists_ClassCategories import populate as populate_LCC
from esp.program.models import Program, ProgramModule
from esp.accounting.controllers import ProgramAccountingController
from django.contrib.auth.models import Group

#   Changed this function to accept a dictionary so that it can be called directly
#   from code in addition to being used in the program creation form.  -Michael P 8/18/2009
def prepare_program(program, data):
    """ This function adds custom stuff to save_instance to facilitate making programs happen.
    """

    #   Permissions format:
    perms = []
    modules = []

    perms += [('Student/All', None, data['student_reg_start'], data['student_reg_end'])] #it is recursive
    perms += [('Student/Catalog', None, data['student_reg_start'], None)]
    perms += [('Student/Profile', None, data['student_reg_start'], None)]
    perms += [('Teacher/All', None, data['teacher_reg_start'], data['teacher_reg_end'])]
    perms += [('Teacher/Classes/View', None, data['teacher_reg_start'], None)]
    perms += [('Teacher/MainPage', None, data['teacher_reg_start'], None)]
    perms += [('Teacher/Profile', None, data['teacher_reg_start'], None)]
    
    #   Grant onsite bit (for all times) if an onsite user is available.
    if ESPUser.onsite_user():
        perms += [('Onsite', ESPUser.onsite_user(), None, None)]
    
    json_module = ProgramModule.objects.get(handler=u'JSONDataModule')  # get the JSON Data Module
    # If the JSON Data Module isn't already in the list of selected
    # program modules, add it. The JSON Data Module is a dependency for
    # many commonly-used modules, so it is important that it be enbabled
    # by default for all new programs.
    if json_module.id not in data['program_modules']:
        data['program_modules'].append(json_module.id)
    modules += [(str(ProgramModule.objects.get(id=i)), i) for i in data['program_modules']]
       
    return perms, modules

def commit_program(prog, perms, modules, cost=0, sibling_discount=None):
    #   This function implements the changes suggested by prepare_program.
    
    def gen_perm(tup):
        new_perm=Permission(permission_type=tup[0], program=prog)

        if tup[2]:
            new_perm.start_date = tup[2]
        if tup[3]:
            new_perm.end_date = tup[3]

        if tup[1] is not None:
            new_perm.user=tup[1]
            new_perm.save()
            return
        elif tup[1] is None and tup[0].startswith("Student"):
            new_perm.role=Group.objects.get(name="Student")
            new_perm.save()
            return
        elif tup[1] is None and tup[0].startswith("Teacher"):
            new_perm.role=Group.objects.get(name="Teacher")
            new_perm.save()
            return

        #It's not for a specific user and not a teacher or student deadline
        for x in ESPUser.getTypes():
            newnew_perm=Permission(permission_type=new_perm.permission_type, role=Group.objects.get(name=x), start_date=new_perm.start_date, end_date=new_perm.end_date, program=prog)
            newnew_perm.save()

    for perm_tup in perms:
        gen_perm(perm_tup)

    pac = ProgramAccountingController(prog)
    pac.setup_accounts()
    pac.setup_lineitemtypes(cost)
    prog.sibling_discount = sibling_discount # property saves Tag, no explicit save needed

    return prog
