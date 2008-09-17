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

matrix_status_dict = {  'N/A': '#999999', 
                        'Empty': '#FFFFFF', 
                        'Conflict': '#FF6666'}

list_status_dict = {'Needs time': '#996600',
                    'Needs room': '#000066',
                    'Needs resources': '#990066',
                    'Happy': '#009900'}


@register.filter
def matrix_td(status_str):
    
    if status_str in matrix_status_dict:
        tdcolor = matrix_status_dict[status_str]
    else:
        tdcolor = '#CCFFDD'
        
    return '<td class="black" style="background-color: %s">%s</td>' % (tdcolor, status_str)
    
        
@register.filter
def color_needs(status_str):
    
    if status_str in list_status_dict:
        color = list_status_dict[status_str]
    else:
        color = '#330033'
        
    return '<span style="color: %s">%s</span>' % (color, status_str)
