from esp.accounting.controllers import ProgramAccountingController
from esp.program.models import Program


def get_donation_total(prog_name):
    prog = Program.objects.get(url=prog_name)
    pac = ProgramAccountingController(prog)
    transfers = pac.all_transfers()
    total = 0
    for t in transfers:
        if 'donation' in str(t.line_item).lower():
            total += t.amount
    return total

if __name__ == '__main__':
    name = raw_input("Enter program URL (e.g. 'Splash/2020_Fall' without quotes): ")
    print('Your total is ${0:.2f}.'.format(get_donation_total(name.strip())))

