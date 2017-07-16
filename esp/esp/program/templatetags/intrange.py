from django import template

register = template.Library()

@register.filter
def intrange(min_val, max_val):
    return range(int(min_val), int(max_val) + 1)
