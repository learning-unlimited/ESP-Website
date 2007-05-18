from django.conf import settings
from django import template
from esp.users.models import ESPUser
from django.http import urlencode
from django.core.cache import cache
from esp.web.util.template import cache_inclusion_tag
register = template.Library()

def cache_key(context):
    try:
        request = context['request']
    except KeyError:
        return None

    if not request.user.is_authenticated():
        return "LEFTBAR__%s" % request.path

    return 'LEFTBAR__%s__%s' % (request.path,
                                urlencode(request.user.id))


@cache_inclusion_tag(register,'inclusion/web/navbar_left.html', takes_context = True, cache_key_func=cache_key)
def navbar_gen(context):
    try:
        request = context['request']
    except KeyError:
        request = {}

    try:
        navbar = context['navbar_list']
    except:
        from esp.web.util.main import default_navbar_data
        navbar = default_navbar_data
    
    return {'navbar_list': navbar.value,
            'request':     request}
    
        
