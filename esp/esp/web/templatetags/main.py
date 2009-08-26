from django import template
register = template.Library()

@register.filter
def split(str,splitter):
    return str.split(splitter)

@register.filter
def concat(str,text):
    return str + text

