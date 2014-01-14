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
def extract_theme(url):
    #   Get the appropriate color scheme out of the Tag that controls nav structure
    #   (specific to MIT theme)
    tab_index = 0
    tc = ThemeController()
    settings = tc.get_template_settings()
    url_dir = os.path.dirname(url)
    for category in settings['nav_structure']:
        category_dir = os.path.dirname(category['header_link'])
        if url_dir.startswith(category_dir):
            i = 1
            for item in category['links']:
                item_dir = os.path.dirname(item['link'])
                if url_dir.startswith(item_dir):
                    tab_index = i
                    break
                i += 1
    return 'tabcolor%d' % tab_index

@register.filter
def get_nav_category(path):
    tc = ThemeController()
    settings = tc.get_template_settings()
                #   Search for current nav category based on request path
    first_level = ''.join(path.lstrip('/').split('/')[:1])
    for category in settings['nav_structure']:
        if category['header_link'].lstrip('/').startswith(first_level):
            return category
    #   Search failed - use default nav category
    default_nav_category = 'learn'
    for category in settings['nav_structure']:
        if category['header_link'].lstrip('/').startswith(default_nav_category):
            return category

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
