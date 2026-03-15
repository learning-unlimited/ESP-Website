from django import template
from django.utils import timezone

register = template.Library()

@register.simple_tag
def get_current_timezone():
    return timezone.get_current_timezone_name()
