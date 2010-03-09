from django import template
register = template.Library()

@register.filter
def mux_tl(str,type):
    splitstr = str.split("/") # String should be of the format "/learn/foo/bar/index.html"
    if len(splitstr) < 2 or splitstr[0] != "":
        return str
    elif splitstr[1] in ("teach", "learn", "manage", "onsite"):
        return ("/%s/" % type) + "/".join(splitstr[2:])
    else:
        return str

@register.filter
def split(str,splitter):
    return str.split(splitter)

@register.filter
def index(arr,index):
    return arr[index]

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

@register.filter
def extract_theme(str):
    str = (str + '//').split('/')
    return theme.get(str[2],False) or theme.get(str[1],False) or 'yellowgreen'
