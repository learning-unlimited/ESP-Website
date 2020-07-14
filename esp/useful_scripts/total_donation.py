from esp.accounting.controllers import ProgramAccountingController
from esp.program.models import Program

program = Program.objects.get(url='Splash/2017_Fall')
pac = ProgramAccountingController(program)
transfers = pac.all_transfers()

total = 0
for t in transfers:
    if t.line_item_id==342:
        total=total+t.amount

print total
