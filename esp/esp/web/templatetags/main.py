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

    'grey': 'myesp',
    'black': 'manage'
}

@register.filter
def extract_theme(str):
    str = (str + '//').split('/')[2]
    return theme.get(str,'yellowgreen')
