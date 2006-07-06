from esp.datatree.models import GetNode
from esp.program.Lists_ClassCategories import populate as populate_LCC
from esp.program.Lists_EquipmentTypes import populate as populate_LET

def PopulateProgram(program_node):
	for sub_node in ProgramTemplate:
		GetNode(program_node + sub_node)

def populate():
	populate_LCC()
	populate_LET()

ProgramTemplate = (
    '/Critical',
    '/Prospectives',
    '/Prospectives/Teachers',
    '/Prospectives/Students',
    '/Prospectives/Volunteers',
    '/Classes',
    '/Subprograms'
    )
