from esp.program.models import ProgramType

ProgramTypes = (
    'Splash!',
    'HSSP',
    'Delve',
    'Splash on Wheels',
    'Junction',
    'Firehose',
    )


for p_desc in ProgramTypes:
    if ProgramType.objects.filter(program_name=p_desc).count()==0:
        p = ProgramType()
        p.program_name = p_desc
        p.save()

