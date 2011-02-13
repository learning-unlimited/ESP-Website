from django import template
from django.utils.http import urlquote as urlencode
from esp.web.util.template import cache_inclusion_tag
register = template.Library()

def cache_key(context, navbar_type='left'):
    try:
        request = context['request']
    except KeyError:
        return None

    if not request.user.is_authenticated():
        return ('NAVBAR',"%sBAR__%s" % (navbar_type.upper(), urlencode(request.path)))

    return ('NAVBAR','%sBAR__%s__%s' % (navbar_type.upper(), urlencode(request.path),
                                request.user.id))


@cache_inclusion_tag(register,'inclusion/web/navbar_left.html', cache_key_func=cache_key)
def navbar_gen(request_path, user, navbar_list, navbar_type='left'):
    
    return {'navbar_list': navbar_list,
            'request_path': request_path,
            'user': user,
            'navbar_type': navbar_type}
