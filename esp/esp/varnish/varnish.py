import httplib

from esp.tagdict.models import Tag
from django.contrib.sites.models import Site

def get_varnish_host(debug=False):
    """ Obtain the host to send Varnish control requests to.
        If Varnish is not set up, return None.  """
    try:
        from django.conf import settings
        if hasattr(settings, 'VARNISH_HOST') and hasattr(settings, 'VARNISH_PORT'):
            return settings.VARNISH_HOST + ":" + str(settings.VARNISH_PORT)
    except ImportError:
        if debug: print "No proxy cache!"
    return None

#@require_tag('varnish_purge')
def purge_page(url, host=None, debug=False):
    if Tag.getTag('varnish_purge', default='false') == 'false':
        return None

    if host == None:
        host = get_varnish_host(debug=debug)
        if host is None:
            return None

    if debug: print "Purging:", url
    conn = httplib.HTTPConnection(host)
    cur_domain = Site.objects.get_current().domain
    if debug: print "Host:", cur_domain
    conn.request("PURGE", url, "", {'Host': cur_domain, 'Accept-Encoding': 'gzip'})
    ret = conn.getresponse()
    return (ret.status, ret.reason)

def purge_all(host=None, debug=False):
    """ Purge the entire Varnish cache for this site using a BAN request. """

    if host == None:
        host = get_varnish_host(debug=debug)
        if host is None:
            return None

    conn = httplib.HTTPConnection(host)
    cur_domain = Site.objects.get_current().domain
    if debug: print "Executing BAN for host:", cur_domain
    conn.request("BAN", "/", "", {'Host': cur_domain, 'Accept-Encoding': 'gzip'})
    ret = conn.getresponse()
    return (ret.status, ret.reason)
