from django import template
from django.utils.http import urlquote as urlencode
from esp.web.util.template import cache_inclusion_tag
register = template.Library()

@cache_inclusion_tag(register,'inclusion/web/navbar_left.html')
def navbar_gen(request_path, user, navbar_list, navbar_type='left'):
    
    return {'navbar_list': navbar_list,
            'request_path': request_path,
            'user': user,
            'navbar_type': navbar_type}
