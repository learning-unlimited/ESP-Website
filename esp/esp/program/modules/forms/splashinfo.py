from __future__ import absolute_import
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
from esp.program.models import Program
from esp.utils.widgets import RadioSelectWithData

class SiblingDiscountForm(forms.Form):
    siblingdiscount = forms.TypedChoiceField(choices=[], coerce=lambda x: x == 'True')
    siblingname = forms.CharField(max_length=128, required=False)

    def __init__(self, *args, **kwargs):
        if 'program' in kwargs:
            program = kwargs.pop('program')
        else:
            raise KeyError('Need to supply program as named argument to SiblingDiscountForm')
        super(SiblingDiscountForm, self).__init__(*args, **kwargs)
        choices = [(False, 'I am the first in my household enrolling in Splash (+ $' + str(program.base_cost) + ').'),
                   (True, 'I have a sibling already enrolled in Splash (+ $' + str(program.base_cost - program.sibling_discount) + ').')]
        option_data = {False: {'cost': program.base_cost, 'for_finaid': 'true'},
                       True: {'cost': program.base_cost - program.sibling_discount, 'for_finaid': 'true'}}
        self.fields['siblingdiscount'].widget = RadioSelectWithData(option_data=option_data)
        self.fields['siblingdiscount'].choices = choices
        self.fields['siblingdiscount'].initial = True

    def clean(self):
        cleaned_data = super(SiblingDiscountForm, self).clean()
        siblingdiscount = cleaned_data.get("siblingdiscount")
        siblingname = cleaned_data.get("siblingname")
        if siblingdiscount and not siblingname:
            self.add_error('siblingname', "You didn't provide the name of your sibling.")
        elif not siblingdiscount:
            self.cleaned_data['siblingname'] = ""

    def load(self, splashinfo):
        self.initial['siblingdiscount'] = splashinfo.siblingdiscount
        self.initial['siblingname'] = splashinfo.siblingname

    def save(self, splashinfo):
        if 'siblingdiscount' in self.cleaned_data:
            splashinfo.siblingdiscount = self.cleaned_data['siblingdiscount']
        if 'siblingname' in self.cleaned_data:
            splashinfo.siblingname = self.cleaned_data['siblingname']
        splashinfo.submitted = True
        splashinfo.save()
