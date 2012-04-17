import httplib
from sys import stdout, stderr

from esp.tagdict.decorators import require_tag
from esp.tagdict.models import Tag
from django.contrib.sites.models import Site

#@require_tag('varnish_purge')
def purge_page(url, host = None):
    if Tag.getTag('varnish_purge', default='false') == 'false':
        return None

    print "purge_page called"
    if host == None:
        try:
            from django.conf import settings
            host = settings.VARNISH_HOST + ":" + str(settings.VARNISH_PORT)
        except ImportError:
            stderr.write("No proxy cache!\n")
            return False

    stdout.write("Purging: " + str(url) + "\n")
    conn = httplib.HTTPConnection(host)
    cur_domain = Site.objects.get_current().domain
    stdout.write("Host: " + cur_domain + "\n")
    conn.request("PURGE", url, "", {'Host': cur_domain, 'Accept-Encoding': 'gzip'})
    ret = conn.getresponse()
    return (ret.status, ret.reason)
