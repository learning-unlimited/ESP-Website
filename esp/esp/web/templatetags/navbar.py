from django import template
from urllib import quote as urlencode
from esp.web.util.template import cache_inclusion_tag
register = template.Library()

def cache_key(context, navbar_type='left'):
    try:
        request = context['request']
    except KeyError:
        return None

    if not request.user.is_authenticated():
        return ('NAVBAR',"%sBAR__%s" % (navbar_type.upper(), urlencode(str(request.path))))

    return ('NAVBAR','%sBAR__%s__%s' % (navbar_type.upper(), urlencode(str(request.path)),
                                request.user.id))

@cache_inclusion_tag(register,'inclusion/web/navbar_left.html', takes_context = True, cache_key_func=cache_key)
def navbar_gen(context, navbar_type='left'):
    try:
        request = context['request']
    except KeyError:
        request = {}

    try:
        navbar = context['navbar_list'].value
    except:
        navbar = None
        
    title_str = 'Navigation'
    if 'learn' in request.path:
        title_str = 'For Students'
    elif 'teach' in request.path:
        title_str = 'For Teachers'
    elif 'getinvolved' in request.path:
        title_str = 'For Volunteers'
    elif 'about' in request.path:
        title_str = 'About ESP'
    
    return {'navbar_list': navbar,
            'title': title_str,
            'request':     request,
            'navbar_type': navbar_type}
