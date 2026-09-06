from __future__ import absolute_import
from django import template

register = template.Library()


@register.simple_tag
def teacher_visible_flags(cls):
    """Return flags on a class whose flag_type has show_to_teacher=True."""
    return list(cls.flags.filter(flag_type__show_to_teacher=True).select_related('flag_type'))
