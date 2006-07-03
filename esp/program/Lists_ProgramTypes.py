from esp.program.models import ProgramType

ProgramTypeOptions = (
    'Splash!',
    'HSSP',
    'Delve',
    'Splash on Wheels',
    'Junction',
    'Firehose',
    )


def populate():
	for p_desc in ProgramTypeOptions:
	    if ProgramType.objects.filter(program_name=p_desc).count()==0:
	        p = ProgramType()
	        p.program_name = p_desc
	        p.save()
