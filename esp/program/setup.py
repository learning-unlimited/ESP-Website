from esp.watchlists.models import GetNode

def PopulateProgram(program_node):
	for sub_node in ProgramTemplate:
		GetNode(program_node + sub_node)

ProgramTemplate = (
    '/Prospectives',
    '/Prospectives/Teachers',
    '/Prospectives/Students',
    '/Prospectives/Volunteers',
    '/Classes',
    '/Subprograms'
    )
