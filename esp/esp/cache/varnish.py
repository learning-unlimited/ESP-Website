import httplib
from sys import stdout
from esp.settings import VARNISH_HOST, VARNISH_PORT
from esp.tagdict.decorators import require_tag

@require_tag('varnish_purge')
def purge_page(url, host = VARNISH_HOST + ":" + str(VARNISH_PORT)):
    stdout.write("Purging: " + str(url) + "\n")
    conn = httplib.HTTPConnection(host)
    conn.request("PURGE", url)
    ret = conn.getresponse()
    return (ret.status, ret.reason)
