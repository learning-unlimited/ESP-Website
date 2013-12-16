
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
  (see AUTHORS file)

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU Affero General Public License
as published by the Free Software Foundation; either version 3
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public
License along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Contact information:
MIT Educational Studies Program
  84 Massachusetts Ave W20-467, Cambridge, MA 02139
  Phone: 617-253-4882
  Email: esp-webmasters@mit.edu
Learning Unlimited, Inc.
  527 Franklin St, Cambridge, MA 02139
  Phone: 617-379-0178
  Email: web-team@lists.learningu.org
"""

from django.forms.forms import Form, Field, BoundField
from django import forms
from django.forms.util import ErrorList
from django.utils.html import escape, mark_safe
from django.template import loader
from django.core.mail import send_mail

from esp.tagdict.models import Tag
from esp.utils.widgets import CaptchaWidget, DummyWidget

class EmailModelForm(forms.ModelForm):
    """ An extension of Django's ModelForms that e-mails when
        an instance of the model is saved using the form.
        Requires from_addr (string) and destination_addrs (list of strings)
        to be provided as arguments to save().
    """
    def __init__(self, *args, **kwargs):
        super(EmailModelForm, self).__init__(*args, **kwargs)
        for field in self.fields.itervalues():
            if field.required:
                field.widget.attrs['class'] = 'required'
    
    def save(self, from_addr='', destination_addrs=[]):
        result = super(EmailModelForm, self).save()
        self.email(from_addr, destination_addrs)
        return result
        
    def email(self, from_addr, destination_addrs):
        context = {}
        context['instance_name'] = self.instance.__class__.__name__
        context['fields'] = []
        for field in self.fields:
            context['fields'].append({'name': field, 'data': self.data[field]})
        msg_text = loader.render_to_string("email/autoform.txt", context)
        send_mail('Automatic E-mail Form Submission (type: %s)' % context['instance_name'], msg_text, from_addr, destination_addrs)


class SizedCharField(forms.CharField):
    """ Just like CharField, but you can set the width of the text widget. """
    def __init__(self, length=None, *args, **kwargs):
        forms.CharField.__init__(self, *args, **kwargs)
        self.widget.attrs['size'] = length

class StrippedCharField(SizedCharField):
    def clean(self, value):
        return super(StrippedCharField, self).clean(self.to_python(value).strip())

#### NOTE: Python super() does weird things (it's the next in the MRO, not a superclass).
#### DO NOT OMIT IT if overriding __init__() when subclassing these forms

class FormWithRequiredCss(forms.Form):
    """ Form that adds the "required" class to every required widget, to restore oldforms behavior. """
    def __init__(self, *args, **kwargs):
        super(FormWithRequiredCss, self).__init__(*args, **kwargs)
        for field in self.fields.itervalues():
            if field.required:
                if 'class' in field.widget.attrs:
                    field.widget.attrs['class'] += ' required'
                else:
                    field.widget.attrs['class'] = 'required'
                    
class FormWithTagInitialValues(forms.Form):
    def __init__(self, *args, **kwargs):
    
        #   Get tag data in the form of a dictionary: 
        #     field name -> tag to look up for initial value
        if 'tag_map' in kwargs:
            tag_map = kwargs['tag_map']
            tag_defaults = {}
            for field_name in tag_map:
                #   Check for existence of tag
                tag_data = Tag.getTag(tag_map[field_name])
                #   Use tag data as initial value if the tag was found
                if tag_data:
                    tag_defaults[field_name] = tag_data
            if 'initial' not in kwargs:
                kwargs['initial'] = {}
            #   Apply defaults to form quietly (don't override provided values)
            for key in tag_defaults:
                if key not in kwargs['initial']:
                    kwargs['initial'][key] = tag_defaults[key]
            #   Remove the tag_map so as not to confuse other functions
            del kwargs['tag_map']
    
        super(FormWithTagInitialValues, self).__init__(*args, **kwargs)

class FormUnrestrictedOtherUser(FormWithRequiredCss):
    """ Form that implements makeRequired for the old form --- disables required fields at in some cases. """

    def __init__(self, user=None, *args, **kwargs):
        super(FormUnrestrictedOtherUser, self).__init__(*args, **kwargs)
        self.user = user
        if user is None or not (hasattr(user, 'other_user') and user.other_user):
            pass
        else:
            for field in self.fields.itervalues():
                if field.required:
                    field.required = False
                    field.widget.attrs['class'] = None # GAH!

class CaptchaField(Field):
    """ A Captcha form element which evaluates to True or raises a validation
    error depending on whether the user entered the correct text. """
    widget = CaptchaWidget
    detect_login = False
    
    def __init__(self, *args, **kwargs):
        if 'detect_login' in kwargs:
            self.detect_login = kwargs['detect_login']
            del kwargs['detect_login']
        if 'help_text' not in kwargs:
            kwargs['help_text'] = 'If you have an ESP user account, you can log in to make this go away.'
        if 'label' not in kwargs:
            kwargs['label'] = 'Prove you\'re human'

        error_messages = {'required' : 'Please enter the two words displayed.'}
        if 'error_messages' in kwargs:
            error_messages = error_messages.update(kwargs['error_messages'])
        kwargs['error_messages'] = error_messages
            
        local_request = kwargs['request']
        del kwargs['request']
        
        super(CaptchaField, self).__init__(*args, **kwargs)
        
        self.widget.request = local_request
        
        
class CaptchaForm(Form):
    def __init__(self, *args, **kwargs):
        local_request = None
        if 'request' in kwargs:
            local_request = kwargs['request']
            del kwargs['request']
            
        super(CaptchaForm, self).__init__(*args, **kwargs)

        if local_request and not local_request.user.is_authenticated():
            self.fields['captcha'] = CaptchaField(request=local_request, required=True)

class CaptchaModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        local_request = None
        if 'request' in kwargs:
            local_request = kwargs['request']
            del kwargs['request']

        forms.ModelForm.__init__(self, *args, **kwargs)

        if local_request and not local_request.user.is_authenticated():
            self.fields['captcha'] = CaptchaField(request=local_request, required=True)

class DummyField(forms.Field):
    widget = DummyWidget
    def __init__(self, *args, **kwargs):
        super(DummyField, self).__init__(*args, **kwargs)
        #   Set a flag that can be checked in Python code or template rendering
        #   to alter behavior
        #   self.is_dummy_field = True

    def is_dummy_field(self):
        return True

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
                return 0
        
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
                if line_group_safe(field) == 0:
                    row_starter = '<tr>'
                    row_ender = '</tr>'
                else:
                    if (i != 0) and (line_group_safe(fieldlist[i-1][1]) == line_group_safe(field)):
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
                output.append(field_text % {'errors': bf_errors, 'label': label, 'field': unicode(bf), 'help_text': help_text, 'field_width': 35})
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
            
    return mark_safe(new_html_output(self, u'<tr><td colspan="2"><table class="plain" width="100%"><tr>', u'<th>%(label)s</th><td width="%(field_width)d%%">%(errors)s%(field)s%(help_text)s</td>', u'<th colspan="2">%(label)s</th></tr><tr><td colspan="2">%(errors)s%(field)s%(help_text)s</td>', u'<td>%s</td>', '</tr></table></td></tr>', u'<br />%s', False))


def add_fields_to_init(init_func, new_fields):
    
    def _callback(self, *args, **kwargs):
        init_func(self, *args, **kwargs)
        for field_name in new_fields.keys():
            setattr(self, field_name, new_fields[field_name])
    
    return _callback
        
def add_fields_to_class(target_class, new_fields):
    """ Take a class and give it new attributes.  The attribute names are the keys in the new_fields dictionary and the default values are the corresponding values in the dictionary. """
    target_class.__init__ = add_fields_to_init(target_class.__init__, new_fields)
