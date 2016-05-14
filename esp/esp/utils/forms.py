
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
  Email: web-team@learningu.org
"""

from django import forms

from esp.tagdict.models import Tag
from esp.utils.widgets import DummyWidget


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

class DummyField(forms.Field):
    widget = DummyWidget
    def __init__(self, *args, **kwargs):
        super(DummyField, self).__init__(*args, **kwargs)
        #   Set a flag that can be checked in Python code or template rendering
        #   to alter behavior
        #   self.is_dummy_field = True

    def is_dummy_field(self):
        return True
