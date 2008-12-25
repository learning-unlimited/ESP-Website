""" ESP Handler which basically does what Django needs but imports stuff ahead of time. """

import os, sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'esp.settings'
sys.path = ['/esp/web/esp', '/esp/web/esp/esp', '/esp/web/esp/django', '/usr/lib/python2.5/site-packages/'] + sys.path

from django.core.handlers import modpython
from django.core.urlresolvers import RegexURLResolver, RegexURLPattern

from esp import settings
from esp.urls import urlpatterns

def handler(req):
    # mod_python hooks into this function.
    sys.path = ['/esp/esp'] + sys.path
    return modpython.handler(req)

def get_views_for_resolver(resolver, views=None, depth=0):
    """ Mutates the views list object in-place. 
    Places all views found by resolver in there and
    will recursively search for more views.
    """

    if views is None:
        views = []

    MAX_DEPTH = 4
    if depth > MAX_DEPTH:
        return views

    try:
        url_patterns = resolver.url_patterns
    except AttributeError:
        # urls.py doesn't have urlpatterns yet.
        return views

    for pattern in resolver.url_patterns:
        if isinstance(pattern, RegexURLPattern):
            views.append(pattern.callback)
        elif isinstance(pattern, RegexURLResolver):
            get_views_for_resolver(pattern, views, depth + 1)

    return views

url_functions = []

for url in urlpatterns:
    # forcibly import all views
    if isinstance(url, RegexURLPattern):
        url_functions.append(url.callback)
    elif isinstance(url, RegexURLResolver):
        url_functions.extend(get_views_for_resolver(url))
