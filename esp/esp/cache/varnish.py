import httplib
from sys import stdout
from esp.settings import VARNISH_HOST, VARNISH_PORT

def purge_page(url, host = VARNISH_HOST + ":" + str(VARNISH_PORT)):
    stdout.write("Purging: " + str(url) + "\n")
    conn = httplib.HTTPConnection(host)
    conn.request("PURGE", url)
    ret = conn.getresponse()
    return (ret.status, ret.reason)
