from django import template
from esp.tagdict.models import Tag

register = template.Library()


@register.filter
def getTag(key):
    return Tag.getTag(key)

@register.filter
def getBooleanTag(key):
    return Tag.getBooleanTag(key)

@register.filter
def getProgramTag(key, program=None, boolean=False):
    return Tag.getBooleanTag(key)
