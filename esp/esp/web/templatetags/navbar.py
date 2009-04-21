from django import template
from urllib import quote as urlencode
from esp.web.util.template import cache_inclusion_tag
register = template.Library()

def cache_key(context):
    try:
        request = context['request']
    except KeyError:
        return None

    if not request.user.is_authenticated():
        return ('LEFTBAR',"LEFTBAR__%s" % urlencode(str(request.path)))

    return ('LEFTBAR','LEFTBAR__%s__%s' % (urlencode(str(request.path)),
                                request.user.id))


@cache_inclusion_tag(register,'inclusion/web/navbar_left.html', takes_context = True, cache_key_func=cache_key)
def navbar_gen(context):
    try:
        request = context['request']
    except KeyError:
        request = {}

    try:
        navbar = context['navbar_list'].value
    except:
        navbar = None
    
    return {'navbar_list': navbar,
            'request':     request}
