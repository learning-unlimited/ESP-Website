from __future__ import absolute_import
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
def getProgramTag(key, program=None):
    return Tag.getProgramTag(key, program)

@register.filter
def getBooleanProgramTag(key, program=None):
    return Tag.getProgramTag(key, program, boolean=True)
