from django import template
from esp.gen_media.subsectionimages import SubSectionImage
from django.core.cache import cache
from urllib import quote
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


def subsection(value):
    """
    Returns a subsection for ESP.
    """
    if hasattr(settings, 'DISABLE_SUBSECTION_FONT') and \
       settings.DISABLE_SUBSECTION_FONT == True:
        return ''

    # We don't really need this cache, but I imagine a cache lookup is
    # maginally faster than computing a SHA-1? --davidben 2009-01-02
    cache_key = quote('SUBSECTION__%s' % value)
    retVal = cache.get(cache_key)
    if retVal:
        return retVal
    
    image = SubSectionImage(value)
    retVal = '<div class="subsectionname">%s</div>' % image.img

    cache.set(cache_key, retVal, 9999)

    return mark_safe(retVal)

subsection = register.filter(name="subsection")(subsection)
