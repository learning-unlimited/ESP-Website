from django import template

register = template.Library()

@register.filter
def smartypants(value):
    try:
        import esp.smartypants
        return esp.smartypants.smartyPants(value)
    except ImportError:
        return value

