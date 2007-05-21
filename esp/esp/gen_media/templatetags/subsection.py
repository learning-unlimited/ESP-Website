from django import template
from esp.gen_media.models import SubSectionImage
from django.core.cache import cache
from urllib import quote

register = template.Library()
@register.filter(name='subsection')
def subsection(value):
    """
    Returns a subsection for ESP.
    """
    cache_key = quote('SUBSECTION__%s' % value)
    retVal = cache.get(cache_key)
    if retVal:
        return retVal
    
    im, created = SubSectionImage.objects.get_or_create(text = value)
    retVal = '<div class="subsectionname">%s</div>' % im

    cache.set(cache_key, retVal, 9999)

    return retVal
