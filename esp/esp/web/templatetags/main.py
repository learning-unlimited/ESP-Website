from esp.themes.controllers import ThemeController

from django import template

import os.path
import simplejson as json

register = template.Library()

@register.filter
def mux_tl(str,type):
    splitstr = str.split("/") # String should be of the format "/learn/foo/bar/index.html"
    if len(splitstr) < 2 or splitstr[0] != "":
        return str
    elif splitstr[1] in ("teach", "learn", "manage", "onsite", "volunteer"):
        return ("/%s/" % type) + "/".join(splitstr[2:])
    else:
        return str

@register.filter
def split(str,splitter):
    return str.split(splitter)

@register.filter
def index(arr,index):
    try:
        return arr[index]
    except IndexError:
        return ''
    
@register.filter
def concat(str,text):
    return str + text

@register.filter
def equal(obj1,obj2):
    return obj1 == obj2

@register.filter
def notequal(obj1,obj2):
    #print str(obj1) + " != " + str(obj2) + " --> " + str(obj1 != obj2)
    return obj1 != obj2

@register.filter
def bool_or(obj1,obj2):
    #print str(obj1) + " or " + str(obj2) + " --> " + str(obj1 or obj2)
    return obj1 or obj2

@register.filter
def bool_and(obj1,obj2):
    #print str(obj1) + " and " + str(obj2) + " --> " + str(obj1 and obj2)
    return obj1 and obj2
    
@register.filter
def extract_theme(str):
    #   Get the appropriate color scheme out of the Tag that controls nav structure
    #   (specific to MIT theme)
    tab_index = 0
    tc = ThemeController()
    settings = tc.get_template_settings()
    for category in settings['nav_structure']:
        if category['header_link'][:5] == str[:5]:
            i = 1
            for item in category['links']:
                if str == item['link']:
                    tab_index = i
                    break
                path_current = os.path.dirname(str)
                path_tab = os.path.dirname(item['link'])
                if len(path_current) > len(path_tab) and path_current.startswith(path_tab):
                    tab_index = i
                    break
                i += 1
    return 'tabcolor%d' % tab_index

@register.filter
def truncatewords_char(value, arg):
    """
    Truncates a string before a certain number of characters, 
    using as many complete words as possible.

    Argument: Number of characters to truncate before.
    """
    from django.utils.text import truncate_words
    try:
        length = int(arg)
    except ValueError: # Invalid literal for int().
        return value # Fail silently.
    
    txt_spaces = value.split()
    txt_result = ''
    for item in txt_spaces:
        if len(txt_result) + 1 + len(item) < length:
            txt_result += ' ' + item
        else:
            txt_result += ' ...'
            break
            
    return txt_result
    
@register.filter
def as_form_label(str):
    return str.replace('_', ' ').capitalize()
