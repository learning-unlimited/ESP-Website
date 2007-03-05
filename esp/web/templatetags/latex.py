""" ESP Custom Filters for template """

from django import template
from esp.gen_media.models import LatexImage
from django.http import HttpResponse
register = template.Library()

@register.filter
def texescape(value):
    """ This will escape a string according to the rules of LaTeX """

    value = str(value).strip()

    special_backslash = '!**ABCDEF**!' # something unlikely to be repeated


    # we will make escape all the strings except those sandwiched between
    # $$ and $$. Thus you can write math symbols like $$\sqrt{3}$$ and
    # get away with it.
    strings = value.split('$$')
    for i in range(len(strings)):
        if i % 2 == 1 and i < len(strings) - 1:
            continue
        strings[i] = strings[i].replace('\\', special_backslash)
        for char in '&$%#_{}':
            strings[i] = strings[i].replace(char, '\\' + char)
        strings[i] = strings[i].replace(special_backslash, '$\\backslash$')
    

    value = '$'.join(strings)


    # now we have to make quotes pretty...
    strings = value.split('"')

    value = strings[0]
    for i in range(1, len(strings)):
        if i % 2 == 1:
            value += '``' + strings[i]
        else:
            value += "''" + strings[i]

    # deal with new-lines
    value = value.replace('\r\n', '\n')
    value = value.replace('\r',   '\n')
    value = value.replace('\n',   '\\\\\n')
    
    return value

@register.filter
def teximages(value,dpi=200):

    value = str(value).strip()

    strings = value.split('$$')

    converted = [ False for i in range(len(strings)) ]

    for i in range(len(strings)):
        if i % 2 == 1 and i < len(strings) - 1:
            if len(strings[i].strip()) > 0:
                converted[i] = True
                try:
                    cur_img, created = LatexImage.objects.get_or_create(content = strings[i])
                    strings[i] = cur_img.getImage()
                except:
                    strings[i] = strings[i]

    value = strings[0]

    for i in range(1,len(strings)):
        if converted[i] or converted[i-1]:
            value += strings[i]
        else:
            value += '$$' + strings[i]
        
    return value



