from django import template
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape


register = template.Library()

def smartypants(value, autoescape=None):
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x

    try:
        import esp.smartypants
        return mark_safe(esp.smartypants.smartyPants(esc(value)))
    except ImportError:
        return value

smartypants.needs_autoescape = True

smartypants = register.filter(smartypants)
