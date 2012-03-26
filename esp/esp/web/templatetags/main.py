from django import template
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
#theme would serve as a default template scheme
theme = {
    '': 'yellowgreen',
    'Splash': 'blue',
    'Spark': 'purple',
    'HSSP': 'red',
    'SATPrep': 'orange',
    'Junction': 'yellow',
    'Delve': 'lightgreen',
    'ProveIt': 'darkgreen',

    #'myesp': 'grey',
    'manage': 'black'
}

#provide a {{ '{ "":"color1","Splash":"color2","Spark":"color3"}'|get_colors}} in the template override 
@register.filter
def get_colors(json_str):
    try:
        json_arr=json.loads(json_str)
        for i in theme.keys():
            theme[i]=str(json_arr.get(i,False))
    except:
        pass
    
@register.filter
def extract_theme(str):
    str = (str + '//').split('/')
    return theme.get(str[2],False) or theme.get(str[1],False) or 'yellowgreen'


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
