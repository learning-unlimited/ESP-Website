from esp.watchlists.models import GetNode

def PopulateInitialDataTree():
    for i in TreeMap:
        GetNode(i)
    
# Q = Qualifier/Series/Category
# V = Verb
TreeMap = (
    'Q',
    'Q/Programs',
    'Q/Programs/_template',
    'Q/Programs/_template/Prospectives',
    'Q/Programs/_template/Prospectives/Teachers',
    'Q/Programs/_template/Prospectives/Students',
    'Q/Programs/_template/Prospectives/Volunteers',
    'Q/Programs/_template/Classes',
    'Q/Programs/_template/Subprograms',
    'Q/Administrivia',
    'Q/Administrivia/Meetings',
    'Q/Administrivia/OrganizationalProjects',
    'Q/ESP',
    'Q/ESP/Committees',
    'Q/ESP/Committees/Webministry',
    'Q/ESP/Committees/Membership',
    'Q/Community',
    'Q/Community/6_12',
    'Q/Community/6_12/Grade6',
    'Q/Community/6_12/Grade7',
    'Q/Community/6_12/Grade8',
    'Q/Community/6_12/Grade9',
    'Q/Community/6_12/Grade10',
    'Q/Community/6_12/Grade11',
    'Q/Community/6_12/Grade12',
    'Q/Community/Prefrosh',
    'Q/Community/Member',
    'Q/Web',
    'V',
    'V/MIT',
    'V/dbmail',
    'V/dbmail/Subscribe',
    'V/registrar',
    'V/registrar/Deadline',
    'V/registrar/Administer',
    )
