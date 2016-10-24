__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2010 by the individual contributors
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
from esp.program.models import PhaseZeroRecord
from esp.utils.widgets import DateTimeWidget
from esp.users.models import ESPUser
from esp.tagdict.models import Tag

class SubmitForm(forms.Form):


    def __init__(self, *args, **kwargs):
        if 'program' in kwargs:
            self.program = kwargs['program']
            del kwargs['program']
        else:
            raise KeyError('Need to supply program as named argument to SubmitForm')
        super(SubmitForm, self).__init__(*args, **kwargs)

    def save(self, user, program):
        #Create new lottery record and assign new lottery number
        rec = PhaseZeroRecord()
        rec.lottery_number = 0
        rec.user = user
        rec.program = program
        rec.save()
        rec.lottery_number = rec.id
        rec.save()

class LotteryNumberForm(forms.Form):

    lottery_number = forms.IntegerField(max_value=999999,min_value=0, label="Group Lottery Code:")

    def __init__(self, *args, **kwargs):
        if 'program' in kwargs:
            self.program = kwargs['program']
            del kwargs['program']
        else:
            raise KeyError('Need to supply program as named argument to LotteryNumberForm')
        super(LotteryNumberForm, self).__init__(*args, **kwargs)

    def load(self, user, program):
        #Load assigned lottery number associated with user
        self.fields['lottery_number'].initial = PhaseZeroRecord.objects.filter(user=user, program=program)[0].lottery_number

    def save(self, user, program):
        #Save new lottery number
        rec = PhaseZeroRecord.objects.filter(user=user, program=program)[0]
        rec.lottery_number = self.cleaned_data['lottery_number']
        rec.save()
