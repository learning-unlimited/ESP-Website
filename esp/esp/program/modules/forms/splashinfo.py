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
import simplejson as json

from esp.accounting.models import LineItemType



class SplashInfoForm(forms.Form):
    """
    The SplashInfoForm is customizable for different lunch options.
    The interface (including directions, whether to exclude or rename days,
    and costs) should be controlled by overriding the template:
        program/modules/splashinfomodule/splashinfo.html
    """
    #   The default choices are somewhat unappetizing...
    default_choices = [['no', 'No'], ['yes', 'Yes']]
    discount_choices = [(False, 'I am the first in my household enrolling in Splash (+ $40)'),
                        (True, 'I have a brother/sister already enrolled in Splash  (+ $20).')]
                  
    lunchsat = forms.ChoiceField(choices=default_choices)
    lunchsun = forms.ChoiceField(choices=default_choices)
    siblingdiscount = forms.ChoiceField(choices=discount_choices, widget=forms.RadioSelect)
    siblingname = forms.CharField(max_length=128, required=False)
    
    def __init__(self, *args, **kwargs):
        #   Extract a program if one was provided
        if 'program' in kwargs:
            self.program = kwargs['program']
            del kwargs['program']
        else:
            self.program = None
        #   Run default init function
        super(SplashInfoForm, self).__init__(*args, **kwargs)
        if self.program:
            lunch_types = [('lunchsat', 'Saturday Lunch'), 
                           ('lunchsun', 'Sunday Lunch'),
                           ('siblingdiscount', 'Sibling Discount'),
                          ]
            for fieldname, line_item_text in lunch_types:
                field = self.fields[fieldname]
                field.choices = self._get_field_choices(fieldname, line_item_text)

                if not field.choices:
                    del self.fields[fieldname]

        if not self.fields.get('siblingdiscount'):
            del self.fields['siblingname']

    def _get_field_choices(self, fieldname, line_item_text):
        lineitem_qset = LineItemType.objects.filter(program=self.program, text=line_item_text)
        choices = []

        if lineitem_qset.exists():
            line_item_type = lineitem_qset[0]

            for li in line_item_type.lineitemoptions_set.all():
                label = '%s (+ $%s)'%(li.description, li.amount)
                choices.append((li.id, label))

        return choices

    def load(self, splashinfo):
        #TODO - Load data from Transfer instance
        self.initial['lunchsat'] = splashinfo.lunchsat
        self.initial['lunchsun'] = splashinfo.lunchsun
        self.initial['siblingdiscount'] = splashinfo.siblingdiscount
        self.initial['siblingname'] = splashinfo.siblingname

    def save(self, splashinfo):
        #TODO - Save data to Transfer instance
        if 'lunchsat' in self.cleaned_data:
            splashinfo.lunchsat = self.cleaned_data['lunchsat']
        if 'lunchsun' in self.cleaned_data:
            splashinfo.lunchsun = self.cleaned_data['lunchsun']
        if 'siblingdiscount' in self.cleaned_data:
            splashinfo.siblingdiscount = eval(self.cleaned_data['siblingdiscount'])
        if 'siblingname' in self.cleaned_data:
            splashinfo.siblingname = self.cleaned_data['siblingname']
        splashinfo.submitted = True
        splashinfo.save()

