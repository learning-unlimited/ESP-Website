
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
from esp.datatree.models import *
from esp.users.models import ESPUser, User, UserBit
from esp.users.models.userbits import UserBitImplication
from esp.program.Lists_ClassCategories import populate as populate_LCC
from esp.program.models import Program, ProgramModule
from esp.accounting_core.models import LineItemType

#   Changed this function to accept a dictionary so that it can be called directly
#   from code in addition to being used in the program creation form.  -Michael P 8/18/2009
def prepare_program(program, data):
    """ This function adds custom stuff to save_instance to facilitate making programs happen.
    """

    #   Datatrees format: each item is a tuple of (node URI, friendly name)
    datatrees = []
    #   Userbits format: each item is a tuple of (QSC URI, user ID, startdate, enddate)
    userbits = []
    modules = []

    # Fetch/create the program node
    program_node_name = program.anchor.uri + '/' + data['term']

    # Create the DataTree branches
    for sub_node in ProgramTemplate:
        datatrees += [(program_node_name + sub_node, '')]

    userbits += [('V/Flags/Public', '(all)', data['publish_start'], data['publish_end'])]
    
    userbits += [('V/Deadline/Registration/Student', '(all)', data['student_reg_start'], data['student_reg_end'])]
    #userbits += [('V/Deadline/Registration/Student/Applications', 0, data['student_reg_start'], data['student_reg_end'])]
    #userbits += [('V/Deadline/Registration/Student/Catalog', 0, data['student_reg_start'], None)]
    #userbits += [('V/Deadline/Registration/Student/Classes', 0, data['student_reg_start'], data['student_reg_end'])]
    #userbits += [('V/Deadline/Registration/Student/Classes/OneClass', 0, data['student_reg_start'], data['student_reg_end'])]
    #userbits += [('V/Deadline/Registration/Student/Confirm', 0, data['student_reg_start'], data['publish_end'])]
    #userbits += [('V/Deadline/Registration/Student/ExtraCosts', 0, data['student_reg_start'], data['student_reg_end'])]
    #userbits += [('V/Deadline/Registration/Student/MainPage', 0, data['student_reg_start'], data['publish_end'])]
    #userbits += [('V/Deadline/Registration/Student/Payment', 0, data['student_reg_start'], data['publish_end'])]
    
    userbits += [('V/Deadline/Registration/Teacher', '(all)', data['teacher_reg_start'], data['teacher_reg_end'])]
    #userbits += [('V/Deadline/Registration/Teacher/Catalog', 0, data['teacher_reg_start'], None)]
    #userbits += [('V/Deadline/Registration/Teacher/Classes', 0, data['teacher_reg_start'], data['teacher_reg_end'])]
    #userbits += [('V/Deadline/Registration/Teacher/Classes/View', 0, data['teacher_reg_start'], data['publish_end'])]
    #userbits += [('V/Deadline/Registration/Teacher/MainPage', 0, data['teacher_reg_start'], data['publish_end'])]
    
    for director in data['admins']:
        userbits += [('V/Administer', ESPUser.objects.get(id=int(director)), None, None)]
        
    modules += [(str(ProgramModule.objects.get(id=i)), i) for i in data['program_modules']]
       
    return datatrees, userbits, modules

def commit_program(prog, datatrees, userbits, modules, costs = (0, 0)):
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
        if (tup[1] is None) or (tup[1] == 0) or (tup[1] == '(all)'):
            new_ub.user = None
        elif type(tup[1]) in (User, ESPUser):
            new_ub.user = tup[1]
        else:
            new_ub.user = ESPUser.objects.get(id=tup[1])        
        new_ub.save()
        return new_ub
        
    for dt_tup in datatrees:
        gen_tree_node(dt_tup)
    
    for ub_tup in userbits:
        gen_userbit(ub_tup)

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
    
