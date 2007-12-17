__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""

from django import template

register = template.Library()

@register.filter
def intrange(min_val, max_val):
    return range(int(min_val), int(max_val) + 1)
    
@register.filter
def field_width(min_val, max_val):
    return '%d%%' % (70 / (int(max_val) - int(min_val) + 1))
    
@register.filter
def substitute(input_str, item):
    #   Puts all of the attributes of the given item in the context dictionary
    t = template.Template(input_str)
    c = template.Context(item.__dict__)
    return t.render(c)

@register.filter
def uselist(input_str, lst):
    #   Takes a list of stuff and puts it in context as 'lst'
    t = template.Template(input_str)
    c = template.Context({'lst': lst})
    return t.render(c)

@register.filter
def tally(lst):
    #   Takes a list and returns a dictionary of entry: frequency
    d = {}
    for item in lst:
        if d.has_key(str(item)):
            d[str(item)] += 1
        else:
            d[str(item)] = 1
    return d

@register.filter
def weighted_avg(dct):
    #   Takes a dictionary of number: freq. and returns weighted avg. (float)
    #   Accepts "Yes", "True" as 1 and "No", "False" as 0.
    s = 0.0
    n = 0
    for key in dct.keys():
        try:
            weight = int(key, 10)
        except TypeError:
            weight = 0
            if ['yes', 'true'].count(lower(key)) > 0:
                weight = 1
        s += weight * dct[key]
        n += dct[key]
    
    if n == 0:
        return 0
    else:
        return s / n

@register.filter
def stripempty(lst):
    #   Takes a list and deletes empty entries. Whitespace-only is empty.
    return [ item for item in lst if len(str(item).strip()) > 0 ]

@register.filter
def makelist(lst):
    #   Because I can't understand Django's built-in unordered_list -ageng
    if len(lst) == 0:
        return "No responses"
    result = ""
    for item in lst:
        result += "<li>" + item + "</li>"
    return result

@register.filter
def numeric_stats(lst, n):
    t = tally(lst)
    a = weighted_avg(t)
    result = '<ul><li> mean: ' + ( '%.2f' % a ) + '</li></ul>'
    result += '<ul>'
    for i in range(1, n+1):
        if not t.has_key(str(i)):
            t[str(i)] = 0
        result += '<li>' + str(i) + ': ' + str(t[str(i)]) + '</li>'
    result += '</ul>'
    return result

@register.filter
def boolean_stats(lst):
    t = tally(lst)
    a = 100 * weighted_avg(t)
    result = '<ul><li> % "Yes": ' + ( '%.2f' % a ) + '</li></ul>'
    result += '<ul>'
    for i in ['Yes', 'No']:
        if not t.has_key(str(i)):
            t[str(i)] = 0
        result += '<li>' + str(i) + ': ' + str(t[str(i)]) + '</li>'
    result += '</ul>'
    return result
