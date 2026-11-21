from __future__ import absolute_import
from django import template

from esp.utils.models import Printer

register = template.Library()


@register.simple_tag
def print_locations():
    """The locations a document can be printed to, Default first."""
    return list(Printer.objects.active().order_by('-is_default', 'name'))
