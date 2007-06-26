
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
from esp.datatree.models import GetNode, DataTree
from esp.users.models import UserBit
from esp.program.Lists_ClassCategories import populate as populate_LCC
from esp.program.models import Program
#	from esp.program.Lists_EquipmentTypes import populate as populate_LET

def PopulateProgram(program_node,
		program_term,
		program_admins,
		teacher_reg_range,
		student_reg_range,
		publish_range):
	""" PopulateProgram initializes a program, establishing its Data Tree branch and
	creating its registration deadline and administration permissions
	"""

	# Fetch/create the program node
	anchor = GetNode( program_node )

	# Set the friendly name for the program's term (e.g. 'Summer 2006')
	anchor.friendly_name = program_term
	anchor.save()

	# Create a Program entry
	program = Program()
	program.anchor = anchor
	program.grade_min = 6
	program.grade_max = 12
	program.class_size_min = 4
	program.class_size_max = 200

	# Create the DataTree branches
	for sub_node in ProgramTemplate:
		GetNode(program_node + sub_node)

	# Create the initial deadline authorizations
	if student_reg_range is not None:
		deadline_student = UserBit()
		deadline_student.user = None
		deadline_student.qsc = anchor
		deadline_student.verb = GetNode( 'V/Deadline/Registration/Student' )
		deadline_student.startdate = student_reg_range[0]
		deadline_student.enddate = student_reg_range[1]
		deadline_student.save()
	if teacher_reg_range is not None:
		deadline_teacher = UserBit()
		deadline_teacher.user = None
		deadline_teacher.qsc = anchor
		deadline_teacher.verb = GetNode( 'V/Deadline/Registration/Teacher' )
		deadline_teacher.startdate = teacher_reg_range[0]
		deadline_teacher.enddate = teacher_reg_range[1]
		deadline_teacher.save()

	# Create the administration authorizations
	admin_verb = GetNode( 'V/Administer' )
	for director in program_admins:
		admin_perm = UserBit()
		admin_perm.user = director
		admin_perm.qsc = anchor
		admin_perm.verb = admin_verb
		admin_perm.save()
	
	# Create the publishing authorizations
	publish_verb = GetNode( 'V/Flags/Public' )
	publish = UserBit()
	publish.user = None
	publish.qsc = anchor
	publish.verb = publish_verb
	publish.startdate = publish_range[0]
	publish.enddate = publish_range[1]
	publish.save()
		
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
    '/Subprograms'
    )

VerbNodes = (
		'V/Flags/Public',
		'V/Deadline/Registration/Teacher',
		'V/Administer',
		'V/Administer/Edit',
		'V/Administer/Edit/QSD',
		'V/Administer/Edit/Class',
		'V/Flags/Registration/Preliminary',
		'V/Flags/Registration/Confirmed'
	    )
# NOTE: V/Flag/Public grants authorization to view a Q branch.
# V/Deadline/Registration/Student enforces the student registration deadline for a program.
# V/Deadline/Registration/Teacher enforces the teacher registration deadline for a program.

