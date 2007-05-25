from django import template


register = template.Library()



@register.filter
def last(list):
    try:
        return list[-1]
    except:
        return ''
