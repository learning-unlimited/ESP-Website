from django import template


register = template.Library()



@register.filter
def last(list):
    try:
        return list[-1]
    except:
        return ''

@register.filter
def startsblock(value, arg):
    return (value % int(arg)) == 0


@register.filter
def endsblock(value, arg):
    return (value % int(arg)) == (int(arg)-1)



