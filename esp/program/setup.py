from esp.watchlists.models import GetNode

def PopulateProgram(program_node):
	for sub_node in ProgramTemplate:
		GetNode(program_node + sub_node)

def populate():
	esp.program.Lists_ClassCategories.populate()
	esp.program.Lists_EquipmentTypes.populate()
	esp.program.Lists_ProgramTypes.populate()

ProgramTemplate = (
    '/Prospectives',
    '/Prospectives/Teachers',
    '/Prospectives/Students',
    '/Prospectives/Volunteers',
    '/Classes',
    '/Subprograms'
    )
