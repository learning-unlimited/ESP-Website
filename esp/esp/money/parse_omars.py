""" Parse the omars file and update the transactions. """

import re

from esp.money.models import Transaction


name_re = re.compile(r"""ESP__(\d+)-(\d+)""")

def parse_omars(file_name):
    """ Parse the omars file and update the transactions.

    Give this a file path, and it should do the rest.
    """

    f = open(file_name, 'r')

    contents = f.read(5000000)

    unfound_ids = []

    for match in name_re.finditer(contents):
        id_ = match.groups()[1]
        
        try:
            transaction = Transaction.objects.get(id = id_)
        except Transaction.DoesNotExist:
            unfound_ids.append(id_)
        else:
            transaction.executed = True
            transaction.save()

    if unfound_ids:
        print """
ALERT: YOU HAVE THE FOLLOWING UNFOUND IDS!

%s""" % unfound_ids
