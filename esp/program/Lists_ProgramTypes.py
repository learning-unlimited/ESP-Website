from esp.program.models import ProgramTypes

ProgramTypesOptions = (
    'Splash!',
    'HSSP',
    'Delve',
    'Splash on Wheels',
    'Junction',
    'Firehose',
    )


def populate():
	for p_desc in ProgramTypeOptions:
	    if ProgramTypes.objects.filter(program_name=p_desc).count()==0:
	        p = ProgramTypes()
	        p.program_name = p_desc
	        p.save()
