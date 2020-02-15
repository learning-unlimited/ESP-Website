from django import template
from django.utils.http import urlquote as urlencode
from esp.utils.cache_inclusion_tag import cache_inclusion_tag
register = template.Library()

@cache_inclusion_tag(register,'inclusion/web/navbar_left.html')
def navbar_gen(request_path, user, navbar_list):

    return {'navbar_list': navbar_list,
            'request_path': request_path,
            'user': user,
            }
