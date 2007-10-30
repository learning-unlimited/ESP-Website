""" Parse the omars file and update the transactions. """

import re

from esp.money.models import Transaction
from urllib import urlencode
from StringIO import StringIO
import pycurl


name_re = re.compile(r"""ESP__(\d+)-(\d+)""")

def fetch_omars(certfile,keyfile,cacert,**options):
    """ Parse the omars file and update the transactions.

    Give this a file path, and it should do the rest.
    """

    query = {
            'Page': 'list',
            'Start': 1,
            'TimeType': 'number',
            'TimeNumber': 14,
            'Filter': 'all',
            'OrdersPerPage': 2000
    }
    query.update(options)
    url = 'https://omars.mit.edu:444/omars/esp_om?' + urlencode(query)

    c = pycurl.Curl()
    sio = StringIO()
    c.setopt(pycurl.SSLKEY, keyfile)
    c.setopt(pycurl.SSLCERT, certfile)
    c.setopt(pycurl.CAINFO, cacert)
    c.setopt(pycurl.URL,url)
    c.setopt(pycurl.WRITEFUNCTION,sio.write)

    c.perform()

    sio.seek(0)
    contents = sio.getvalue()

    unfound_ids = []

    for match in name_re.finditer(contents):
        id_ = match.groups()[1]
        
        try:
            transaction = Transaction.objects.get(id = id_)
        except Transaction.DoesNotExist:
            unfound_ids.append(id_)
        else:
            if not transaction.executed:
                    print 'found:', str(transaction)
		    transaction.executed = True
		    transaction.save()

    if unfound_ids:
        print """
ALERT: YOU HAVE THE FOLLOWING UNFOUND IDS!

%s""" % unfound_ids
