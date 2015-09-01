from django import template
from django.utils.http import urlquote as urlencode
from esp.utils.cache_inclusion_tag import cache_inclusion_tag
from esp.web.models import NavBarCategory, NavBarEntry
from esp.web.views.navBar import makeNavBar

register = template.Library()

@cache_inclusion_tag(register,'inclusion/web/navbar_left.html')
def navbar_gen(request_path, user, navbar_list, navbar_type='left'):

    return {'navbar_list': navbar_list,
            'request_path': request_path,
            'user': user,
            'navbar_type': navbar_type}

# So I'm cheating here because I couldn't figure out a neat way to
# do what Chicago wanted using their existing infrastructure.
# Maybe I'll eventually move this to template overrides.
# -ageng 2013-08-12
@cache_inclusion_tag(register,'inclusion/web/navbar_entries.html')
def navbar_by_category(cat):
    try:
        cat = NavBarCategory.objects.get(name=cat)
    except (NavBarCategory.DoesNotExist, NavBarCategory.MultipleObjectsReturned):
        cat = None
    navbar_list = makeNavBar('', cat)
    return {'navbar_list': navbar_list}
navbar_by_category.cached_function.depend_on_row(NavBarEntry, lambda entry: {'cat': entry.category.name})
