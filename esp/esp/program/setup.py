
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
  Email: web-team@lists.learningu.org
"""
from esp.datatree.models import *
from esp.users.models import ESPUser, User, UserBit, Permission
from esp.users.models.userbits import UserBitImplication
from esp.program.Lists_ClassCategories import populate as populate_LCC
from esp.program.models import Program, ProgramModule
from esp.accounting_core.models import LineItemType
from django.contrib.auth.models import Group

#   Changed this function to accept a dictionary so that it can be called directly
#   from code in addition to being used in the program creation form.  -Michael P 8/18/2009
def prepare_program(program, data):
    """ This function adds custom stuff to save_instance to facilitate making programs happen.
    """

    #   Datatrees format: each item is a tuple of (node URI, friendly name)
    datatrees = []
    #   Userbits format: each item is a tuple of (QSC URI, user ID, startdate, enddate)
    userbits = []
    #   Permissions format:
    perms = []
    modules = []

    # Fetch/create the program node
    program_node_name = program.anchor.get_uri() + '/' + data['term']

    # Create the DataTree branches
    for sub_node in ProgramTemplate:
        datatrees += [(program_node_name + sub_node, '')]

    userbits += [('V/Flags/Public', None, data['publish_start'], data['publish_end'])]
    perms += [('View', None, data['publish_start'], data['publish_end'])]
    
    userbits += [('V/Deadline/Registration/Student', None, data['student_reg_start'], data['student_reg_end'])]
    perms += [('Student/All', None, data['student_reg_start'], data['student_reg_end'])] #it is recursive

    #userbits += [('V/Deadline/Registration/Student/Applications', None, data['student_reg_start'], data['student_reg_end'])]
    userbits += [('V/Deadline/Registration/Student/Catalog', None, data['student_reg_start'], None)]
    perms += [('Student/Catalog', None, data['student_reg_start'], None)]
    #userbits += [('V/Deadline/Registration/Student/Classes', None, data['student_reg_start'], data['student_reg_end'])]
    #userbits += [('V/Deadline/Registration/Student/Classes/OneClass', None, data['student_reg_start'], data['student_reg_end'])]
    #userbits += [('V/Deadline/Registration/Student/Confirm', None, data['student_reg_start'], data['publish_end'])]
    #userbits += [('V/Deadline/Registration/Student/ExtraCosts', None, data['student_reg_start'], data['student_reg_end'])]
    #userbits += [('V/Deadline/Registration/Student/MainPage', None, data['student_reg_start'], data['publish_end'])]
    #userbits += [('V/Deadline/Registration/Student/Payment', None, data['student_reg_start'], data['publish_end'])]
    
    userbits += [('V/Deadline/Registration/Teacher', None, data['teacher_reg_start'], data['teacher_reg_end'])]
    perms += [('Teacher/All', None, data['teacher_reg_start'], data['teacher_reg_end'])]
    #userbits += [('V/Deadline/Registration/Teacher/Catalog', None, data['teacher_reg_start'], None)]
    #userbits += [('V/Deadline/Registration/Teacher/Classes', None, data['teacher_reg_start'], data['teacher_reg_end'])]
    userbits += [('V/Deadline/Registration/Teacher/Classes/View', None, data['teacher_reg_start'], None)]
    perms += [('Teacher/Classes/View', None, data['teacher_reg_start'], None)]
    userbits += [('V/Deadline/Registration/Teacher/MainPage', None, data['teacher_reg_start'], None)]
    perms += [('Teacher/MainPage', None, data['teacher_reg_start'], None)]
    userbits += [('V/Deadline/Registration/Teacher/Profile', None, data['teacher_reg_start'], None)]
    perms += [('Teacher/Profile', None, data['teacher_reg_start'], None)]
    
    #   Grant onsite bit (for all times) if an onsite user is available.
    if ESPUser.onsite_user():
        userbits += [('V/Registration/Onsite', ESPUser.onsite_user(), None, None)]
        perms += [('Onsite', ESPUser.onsite_user(), None, None)]
    
    for director in data['admins']:
        userbits += [('V/Administer', ESPUser.objects.get(id=int(director)), None, None)]
        perms += [('Administer', ESPUser.objects.get(id=int(director)), None, None)]
        
    json_module = ProgramModule.objects.get(handler=u'JSONDataModule')  # get the JSON Data Module
    # If the JSON Data Module isn't already in the list of selected
    # program modules, add it. The JSON Data Module is a dependency for
    # many commonly-used modules, so it is important that it be enbabled
    # by default for all new programs.
    if json_module.id not in data['program_modules']:
        data['program_modules'].append(json_module.id)
    modules += [(str(ProgramModule.objects.get(id=i)), i) for i in data['program_modules']]
       
    return datatrees, userbits, perms, modules

def commit_program(prog, datatrees, userbits, perms, modules, costs = (0, 0)):
    #   This function implements the changes suggested by prepare_program, by actually
    #   creating the necessary datatrees and userbits.
    def gen_tree_node(tup):
        new_node = DataTree.get_by_uri(tup[0], create=True)
        new_node.friendly_name = tup[1]
        new_node.save()
        return new_node
    
    def gen_userbit(tup):
        new_ub = UserBit()
        new_ub.verb = DataTree.get_by_uri(tup[0], create=True)
        new_ub.qsc = prog.anchor
        new_ub.recursive = True
        if tup[2]:
            new_ub.startdate = tup[2]
        if tup[3]:
            new_ub.enddate = tup[3]
        if (tup[1] is None) or (tup[1] == 0):
            new_ub.user = None
        elif type(tup[1]) in (User, ESPUser):
            new_ub.user = tup[1]
        else:
            new_ub.user = ESPUser.objects.get(id=tup[1])        
        new_ub.save()
        return new_ub

    def gen_perm(tup):
        new_perm=Permission(permission_type=tup[0], program=prog)

        if tup[2]:
            new_perm.startdate = tup[2]
        if tup[3]:
            new_perm.enddate = tup[3]

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
            newnew_perm=Permission(permission_type=new_perm.permission_type, role=Group.objects.get(name=x), startdate=new_perm.startdate, enddate=new_perm.enddate, program=prog)
            newnew_perm.save()
        
    for dt_tup in datatrees:
        gen_tree_node(dt_tup)
    
    for ub_tup in userbits:
        gen_userbit(ub_tup)

    for perm_tup in perms:
        gen_perm(perm_tup)

    l = LineItemType()
    l.text = prog.niceName() + " Admission"
    l.amount = -costs[0]
    l.anchor = prog.anchor["LineItemTypes"]["Required"]
    l.finaid_amount = -costs[1]
    l.finaid_anchor = prog.anchor["Accounts"]["FinancialAid"]
    l.save()
        
    #   Create a userbit implication giving permanent registration access to the directors.
    ubi = UserBitImplication()
    ubi.qsc_original = prog.anchor
    ubi.verb_original = DataTree.get_by_uri('V/Administer')
    ubi.qsc_implied = prog.anchor
    ubi.verb_implied = DataTree.get_by_uri('V/Deadline/Registration')
    ubi.recursive = True
    ubi.save()
        
    return prog


def populate():
	populate_LCC()
	#	populate_LET()
	for v_node in VerbNodes:
		GetNode( v_node )

ProgramTemplate = (
    '/Critical',
    '/Internal',
    '/Prospectives',
    '/Prospectives/Teachers',
    '/Prospectives/Students',
    '/Prospectives/Volunteers',
    '/Classes',
    '/Subprograms',
    '/LineItemTypes',
    '/LineItemTypes/Required',
    '/LineItemTypes/Optional',
    '/Announcements',
    '/Announcements/Teachers',
    '/Confirmation',
    '/Accounts',
    '/Accounts/FinancialAid',
    '/TeacherEvents/Interview',
    '/TeacherEvents/Training',
    )

VerbNodes = (
    'V/Deadline/Registration/Student',
    'V/Deadline/Registration/Student/Applications',
    'V/Deadline/Registration/Student/Catalog',
    'V/Deadline/Registration/Student/Classes',
    'V/Deadline/Registration/Student/Classes/OneClass',
    'V/Deadline/Registration/Student/Confirm',
    'V/Deadline/Registration/Student/ExtraCosts',
    'V/Deadline/Registration/Student/Finaid',
    'V/Deadline/Registration/Student/MainPage',
    'V/Deadline/Registration/Student/Payment',
    'V/Deadline/Registration/Teacher',
    'V/Deadline/Registration/Teacher/Catalog',
    'V/Deadline/Registration/Teacher/Classes',
    'V/Deadline/Registration/Teacher/Classes/View',
    'V/Deadline/Registration/Teacher/MainPage',
    'V/Flags/Public',
    'V/Administer',
    'V/Administer/Edit',
    'V/Administer/Edit/QSD',
    'V/Administer/Edit/Class',
    'V/Flags/Registration/Preliminary',
    'V/Flags/Registration/Confirmed',
    )
    
