from django.conf import settings
from django import template
from esp.users.models import ESPUser
from django.http import urlencode
from django.core.cache import cache

register = template.Library()

@register.inclusion_tag('inclusion/web/navbar_left.html', takes_context = True)
def navbar_gen(context):
    try:
        navbar = context['navbar_list']
    except:
        from esp.web.util.main import default_navbar_data
        navbar = default_navbar_data
    

    try:
        request = context['request']
        cache_id = 'LEFTBAR__%s__%s' % (urlencode(request.path),
                                         urlencode(request.user.id))
        retVal = cache.get(cache_id)
        if retVal:
            return retVal
    except:
        
        cache_id = None
        request = None

    

    retVal = {'navbar_list': navbar.value,
              'request':     request}

    if cache_id:
        cache.set(cache_id, retVal, 99999)

    return retVal
    
        
