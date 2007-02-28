""" ESP Custom Filters for template """

from django import template

register = template.Library()

@register.filter
def texescape(value):
    """ This will escape a string according to the rules of LaTeX """

    value = str(value).strip()

    special_backslash = '!**ABCDEF**!' # something unlikely to be repeated

    strings = value.split('$$')
    for i in range(len(strings)):
        if i % 2 == 1 and i < len(strings) - 1:
            continue
        strings[i] = strings[i].replace('\\', special_backslash)
        for char in '&$%#_{}':
            strings[i] = strings[i].replace(char, '\\' + char)
        strings[i] = strings[i].replace(special_backslash, '$\\backslash$')
    

    value = '$$'.join(strings)

    strings = value.split('"')

    value = strings[0]
 
    for i in range(1, len(strings)):
        if i % 2 == 1:
            value += '``' + strings[i]
        else:
            value += "''" + strings[i]

    value = value.replace('\r\n', special_backslash)
    value = value.replace('\n', special_backslash)
    value = value.replace('\r', special_backslash)

    value = value.replace(special_backslash, '\\\\\n')
    
    return value

