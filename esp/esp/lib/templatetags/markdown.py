from esp.lib.markdown import markdown as real_markdown
from django import template

register = template.Library()


@register.filter
def markdown(value):
    return real_markdown(value)
