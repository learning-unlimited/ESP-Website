from django import template
from esp.gen_media.models import SubSectionImage
from django.core.cache import cache
from urllib import quote
from django.conf import settings

register = template.Library()
@register.filter(name='subsection')
def subsection(value):
    """
    Returns a subsection for ESP.
    """
    if hasattr(settings, 'DISABLE_SUBSECTION_FONT') and \
       settings.DISABLE_SUBSECTION_FONT == True:
        return ''

    cache_key = quote('SUBSECTION__%s' % value)
    retVal = cache.get(cache_key)
    if retVal:
        return retVal
    
    im, created = SubSectionImage.objects.get_or_create(text = value)
    retVal = '<div class="subsectionname">%s</div>' % im

    cache.set(cache_key, retVal, 9999)

    return retVal
