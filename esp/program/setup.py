from esp.datatree.models import GetNode, DataTree
from esp.users.models import UserBit
from esp.program.Lists_ClassCategories import populate as populate_LCC
from esp.program.Lists_EquipmentTypes import populate as populate_LET

def PopulateProgram(program_node,
		program_term,
		program_admins,
		teacher_reg_range,
		student_reg_range):
	""" PopulateProgram initializes a program, establishing its Data Tree branch and
	creating its registration deadline and administration permissions
	"""

	# Fetch/create the program node
	anchor = GetNode( program_node )

	# Set the friendly name for the program's term (e.g. 'Summer 2006')
	anchor.friendly_name = program_term
	anchor.update()

	# Create the DataTree branches
	for sub_node in ProgramTemplate:
		GetNode(program_node + sub_node)

	# Create the initial deadline authorizations
	if student_reg_range is not null:
		deadline_student = UserBit()
		deadline_student.user = None
		deadline_student.qsc = anchor
		deadline_student.verb = GetNode( 'V/Deadline/Registration/Student' )
		deadline_student.startdate = student_reg_range[0]
		deadline_student.enddate = student_reg_range[1]
	if teacher_reg_range is not null:
		deadline_teacher = UserBit()
		deadline_teacher.user = None
		deadline_teacher.qsc = anchor
		deadline_teacher.verb = GetNode( 'V/Deadline/Registration/Teacher' )
		deadline_teacher.startdate = teacher_reg_range[0]
		deadline_teacher.enddate = teacher_reg_range[1]

	# Create the administration authorizations
	admin_verb = GetNode( 'V/Administer/Program' )
	for director in program_admins:
		admin_perm = UserBit()
		admin_perm.user = director
		admin_perm.qsc = anchor
		admin_perm.verb = admin_verb
	
	# Create the publishing authorizations
	publish_verb = GetNode( 'V/Publish' )
	publish = UserBit()
	publish.user = None
	publish.qsc = anchor
	publish.verb = publish_verb
	publish.startdate = program_term[0]
	publish.enddate = program_term[1]
		
def populate():
	populate_LCC()
	populate_LET()
	for v_node in VerbNodes:
		GetNode( v_node )

ProgramTemplate = (
    '/Critical',
    '/Prospectives',
    '/Prospectives/Teachers',
    '/Prospectives/Students',
    '/Prospectives/Volunteers',
    '/Classes',
    '/Subprograms'
    )

VerbNodes = (
		'V/Publish',
		'V/Deadline/Registration/Student',
		'V/Deadline/Registration/Teacher',
		'V/Administer/Program',
		'V/Administer/Program/Class',
		'V/Preregister'
	    )
# NOTE: V/Publish grants authorization to view a Q branch.
# V/Deadline/Registration/Student enforces the student registration deadline for a program.
# V/Deadline/Registration/Teacher enforces the teacher registration deadline for a program.
