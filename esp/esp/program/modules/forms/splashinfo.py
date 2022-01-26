__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2009 by the individual contributors
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
from esp.middleware import ESPError
from esp.tagdict.models import Tag
import json

"""
The SplashInfoForm is customizable for different lunch options.
The choices should be provided in a Tag, splashinfo_choices, which is in
JSON format.  Example:
    key = 'splashinfo_choices'
    value = '{
        "lunchsat": [["no", "No thanks; I will bring my own lunch"],
                  ["chicken", "Yes, Chicken"],
                  ["steak", "Yes, Steak"],
                  ["spicy_thai", "Yes, Spicy Thai"],
                  ["veggie", "Yes, Vegetarian"]],
        "lunchsun": [["no", "No thanks; I will bring my own lunch"],
                  ["cheese", "Yes, Cheese Pizza"],
                  ["pepperoni", "Yes, Pepperoni Pizza"]],
    }'

The interface (including directions, whether to exclude or rename days,
and costs) should be controlled by overriding the template:
    program/modules/splashinfomodule/splashinfo.html
"""

class SplashInfoForm(forms.Form):
    #   The default choices are somewhat unappetizing...
    default_choices = [['no', 'No'], ['yes', 'Yes']]
    discount_choices = [(False, 'I am the first in my household enrolling in Splash (+ $40)'),
                        (True, 'I have a sibling already enrolled in Splash  (+ $20).')]

    lunchsat = forms.ChoiceField(choices=default_choices)
    lunchsun = forms.ChoiceField(choices=default_choices)
    siblingdiscount = forms.ChoiceField(choices=discount_choices, widget=forms.RadioSelect)
    siblingname = forms.CharField(max_length=128, required=False)

    def __init__(self, *args, **kwargs):
        #   Extract a program if one was provided
        if 'program' in kwargs:
            program = kwargs['program']
            del kwargs['program']
        else:
            program = None

        #   Run default init function
        super(SplashInfoForm, self).__init__(*args, **kwargs)

        #   Set choices from Tag data (try to get program-specific choices if they exist)
        tag_data = Tag.getProgramTag('splashinfo_choices', program)
        if tag_data:
            tag_struct = json.loads(tag_data)
            self.fields['lunchsat'].choices = tag_struct['lunchsat']
            self.fields['lunchsun'].choices = tag_struct['lunchsun']

        if not Tag.getBooleanTag('splashinfo_siblingdiscount', program=program):
            del self.fields['siblingdiscount']
            del self.fields['siblingname']

        if not Tag.getBooleanTag('splashinfo_lunchsat', program=program):
            del self.fields['lunchsat']

        if not Tag.getBooleanTag('splashinfo_lunchsun', program=program):
            del self.fields['lunchsun']

    def load(self, splashinfo):
        self.initial['lunchsat'] = splashinfo.lunchsat
        self.initial['lunchsun'] = splashinfo.lunchsun
        self.initial['siblingdiscount'] = splashinfo.siblingdiscount
        self.initial['siblingname'] = splashinfo.siblingname

    def save(self, splashinfo):
        if 'lunchsat' in self.cleaned_data:
            splashinfo.lunchsat = self.cleaned_data['lunchsat']
        if 'lunchsun' in self.cleaned_data:
            splashinfo.lunchsun = self.cleaned_data['lunchsun']
        if 'siblingdiscount' in self.cleaned_data:
            splashinfo.siblingdiscount = (self.cleaned_data['siblingdiscount'] == "True")
        if 'siblingname' in self.cleaned_data:
            splashinfo.siblingname = self.cleaned_data['siblingname']
        splashinfo.submitted = True
        splashinfo.save()

