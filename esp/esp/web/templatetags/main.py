from django import template
register = template.Library()

@register.filter
def split(str,splitter):
    return str.split(splitter)

@register.filter
def concat(str,text):
    return str + text

theme = {
    '': 'yellowgreen',
    'Splash': 'blue',
    'Spark': 'purple',
    'HSSP': 'red',
    'SATPrep': 'orange',
    'Junction': 'yellow',
    'Delve': 'lightgreen',
    'ProveIt': 'darkgreen',

    'myesp': 'grey',
    'manage': 'black'
}

@register.filter
def extract_theme(str):
    str = (str + '//').split('/')
    return theme.get(str[2],False) or theme.get(str[1],False) or 'yellowgreen'
