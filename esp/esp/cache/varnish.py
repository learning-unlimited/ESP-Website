import httplib
from sys import stdout, stderr

from esp.tagdict.models import Tag
from django.contrib.sites.models import Site

def get_varnish_host():
    """ Obtain the host to send Varnish control requests to.
        If Varnish is not set up, return None.  """
    try:
        from django.conf import settings
        if hasattr(settings, 'VARNISH_HOST') and hasattr(settings, 'VARNISH_PORT'):
            return settings.VARNISH_HOST + ":" + str(settings.VARNISH_PORT)
    except ImportError:
        stderr.write("No proxy cache!\n")
    return None

#@require_tag('varnish_purge')
def purge_page(url, host = None):
    if Tag.getTag('varnish_purge', default='false') == 'false':
        return None

    if host == None:
        host = get_varnish_host()
        if host is None:
            return None

    stdout.write("Purging: " + str(url) + "\n")
    conn = httplib.HTTPConnection(host)
    cur_domain = Site.objects.get_current().domain
    stdout.write("Host: " + cur_domain + "\n")
    conn.request("PURGE", url, "", {'Host': cur_domain, 'Accept-Encoding': 'gzip'})
    ret = conn.getresponse()
    return (ret.status, ret.reason)

def purge_all(host=None):
    """ Purge the entire Varnish cache for this site using a BAN request. """

    if host == None:
        host = get_varnish_host()
        if host is None:
            return None

    conn = httplib.HTTPConnection(host)
    cur_domain = Site.objects.get_current().domain
    stdout.write("Executing BAN for host: " + cur_domain + "\n")
    conn.request("BAN", "/", "", {'Host': cur_domain, 'Accept-Encoding': 'gzip'})
    ret = conn.getresponse()
    return (ret.status, ret.reason)
