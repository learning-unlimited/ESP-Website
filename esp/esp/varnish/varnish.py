import httplib

from django.conf import settings
from django.contrib.sites.models import Site

def get_varnish_host():
    """ Obtain the host to send Varnish control requests to.
        If Varnish is not set up, return None.  """
    if hasattr(settings, 'VARNISH_HOST') and hasattr(settings, 'VARNISH_PORT'):
        return settings.VARNISH_HOST + ":" + str(settings.VARNISH_PORT)
    else:
        return None

def purge_page(url, host=None):
    if host == None:
        host = get_varnish_host()
        if host is None:
            return None

    conn = httplib.HTTPConnection(host)
    cur_domain = Site.objects.get_current().domain
    conn.request("PURGE", url, "", {'Host': cur_domain, 'Accept-Encoding': 'gzip'})
    ret = conn.getresponse()
    return (ret.status, ret.reason)

def purge_all(host=None):
    """ Purge the entire Varnish cache for this site using a BAN request. """

    if host is None:
        host = get_varnish_host()
        if host is None:
            return None

    conn = httplib.HTTPConnection(host)
    cur_domain = Site.objects.get_current().domain
    conn.request("BAN", "/", "", {'Host': cur_domain, 'Accept-Encoding': 'gzip'})
    ret = conn.getresponse()
    return (ret.status, ret.reason)
