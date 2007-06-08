
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

from django.newforms.forms import BoundField
from django.newforms.util import ErrorList
from django.utils.html import escape

def new_callback(exclude=None, include=None):
    """
    Create a form callback which excludes or only includes certain fields.
    """
    def _callback(field, **kwargs):
        if include and field.name not in include:
            return None
        if exclude and field.name in exclude:
            return None
        return field.formfield(**kwargs)
    return _callback

def grouped_as_table(self):
    """ Modified as_table function to support our own formatting features. """
    def new_html_output(self, def_row_starter, short_field, long_field, error_txt, def_row_ender, help_text_html, errors_on_separate_row):
        "Helper function for outputting HTML. Used by as_table(), as_ul(), as_p()."
        
        def line_group_safe(field):
            if hasattr(field, 'line_group'):
                return field.line_group
            else:
                return -1
        
        def field_compare(field_a, field_b):
            return line_group_safe(field_a[1]) - line_group_safe(field_b[1])
        
        top_errors = self.non_field_errors() # Errors that should be displayed above all fields.
        output, hidden_fields = [], []
        fieldlist = self.fields.items()
        fieldlist.sort(field_compare)

        for i in range(0,len(fieldlist)):
            name = fieldlist[i][0]
            field = fieldlist[i][1]
            row_starter = def_row_starter
            row_ender = def_row_ender
            
            bf = BoundField(self, field, name)
            bf_errors = ErrorList([escape(error) for error in bf.errors]) # Escape and cache in local variable.
            if bf.is_hidden:
                if bf_errors:
                    top_errors.extend(['(Hidden field %s) %s' % (name, e) for e in bf_errors])
                hidden_fields.append(unicode(bf))
            else:
                
                #   Only put in the row break if this field is on a different line group than the previous one
                if line_group_safe(field) == -1:
                    row_starter = '<tr>'
                    row_ender = '</tr>'
                else:
                    if (i > 0) and (line_group_safe(fieldlist[i-1][1]) == line_group_safe(field)):
                        output.append('<!-- Killing starter: prev=%d current=%d -->' % (line_group_safe(fieldlist[i-1][1]), line_group_safe(field)))
                        row_starter = ''
                    if (i < len(fieldlist) - 1) and (line_group_safe(fieldlist[i+1][1]) == line_group_safe(field)):
                        output.append('<!-- Killing ender: current=%d next=%d -->' % (line_group_safe(field),line_group_safe(fieldlist[i+1][1])))
                        row_ender = ''
                
                output.append('<!-- i=%d: begin field line group %d starter="%s" ender="%s" -->' % (i, line_group_safe(field), row_starter, row_ender))
                
                if errors_on_separate_row and bf_errors:
                    output.append(error_row % bf_errors)
                label = bf.label and bf.label_tag(escape(bf.label + ':')) or ''
                if field.help_text:
                    help_text = help_text_html % field.help_text
                else:
                    help_text = u''
                    
                field_text = short_field
                if hasattr(field, 'is_long') and field.is_long:
                    field_text = long_field
                    
                output.append(row_starter)
                output.append(field_text % {'errors': bf_errors, 'label': label, 'field': unicode(bf), 'help_text': help_text})
                output.append(row_ender)

        if top_errors:
            output.insert(0, error_txt % top_errors)
        if hidden_fields: # Insert any hidden fields in the last row.
            str_hidden = '<td>' + u''.join(hidden_fields) + '</td>'
            if output:
                last_row = output[-1]
                # Chop off the trailing row_ender (e.g. '</td></tr>') and insert the hidden fields.
                output[-1] = last_row[:-len(row_ender)] + str_hidden + row_ender
            else: # If there aren't any rows in the output, just append the hidden fields.
                output.append(str_hidden)
        return u'\n'.join(output)
            
    return new_html_output(self, u'<tr><td colspan="2"><table class="plain" width="100%"><tr>', u'<th>%(label)s</th><td>%(errors)s%(field)s%(help_text)s</td>', u'<th colspan="2">%(label)s</th></tr><tr><td colspan="2">%(errors)s%(field)s%(help_text)s</td>', u'<td>%s</td>', '</tr></table></td></tr>', u'<br />%s', False)


def add_fields_to_init(init_func, new_fields):
    
    def _callback(self, *args, **kwargs):
        init_func(self, *args, **kwargs)
        for field_name in new_fields.keys():
            setattr(self, field_name, new_fields[field_name])
    
    return _callback
        
def add_fields_to_class(target_class, new_fields):
    """ Take a class and give it new attributes.  The attribute names are the keys in the new_fields dictionary and the default values are the corresponding values in the dictionary. """
    target_class.__init__ = add_fields_to_init(target_class.__init__, new_fields)
