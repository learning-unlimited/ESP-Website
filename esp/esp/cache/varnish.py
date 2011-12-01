import httplib
from sys import stdout
from esp.settings import VARNISH_HOST

def purge_page(url, host = VARNISH_HOST):
    stdout.write("Purging: " + str(url) + "\n")
    conn = httplib.HTTPConnection(host)
    conn.request("PURGE", url)
    ret = conn.getresponse()
    return (ret.status, ret.reason)
