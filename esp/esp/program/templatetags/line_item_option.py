from __future__ import absolute_import
from django import template

register = template.Library()

@register.filter
def description(option):
    return option[2]

@register.filter

def id(option):
    return option[0]
