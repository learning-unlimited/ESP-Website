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
from esp.program.models import ModeratorRecord
from esp.tagdict.models import Tag

class ModeratorForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        if 'program' in kwargs:
            self.program = kwargs['program']
            del kwargs['program']
        else:
            raise KeyError('Need to supply program as named argument to ModeratorForm')
        super(ModeratorForm, self).__init__(*args, **kwargs)
        self.fields['class_categories'].queryset = self.program.class_categories.all()
        choices = [(0, 'Please select an option')] + [(num, num) for num in range(1, self.program.num_timeslots() + 1)]
        self.fields['num_slots'].choices = choices
        self.fields['num_slots'].widget.choices = choices

        # specify help text/labels with tags
        for field in self.fields.keys():
            tag_data = Tag.getProgramTag('moderatorreg_label_%s' % field, self.program)
            if tag_data:
                self.fields[field].label = tag_data
            tag_data = Tag.getProgramTag('moderatorreg_help_text_%s' % field, self.program)
            if tag_data:
                self.fields[field].help_text = tag_data

    class Meta:
        model = ModeratorRecord
        fields = ('will_moderate', 'num_slots', 'class_categories', 'comments')
        labels = {
            'will_moderate': 'Will you moderate classes?',
            'num_slots': 'Number of timeslots?',
        }
        help_texts = {
            'will_moderate': 'Would you like to moderate the classes of other teachers?',
            'num_slots': 'How many timeslots can you moderate (we will use your teacher availability)?',
            'class_categories': 'Which categories of classes are you most interested in moderating?',
        }
        widgets = {
            'num_slots': forms.widgets.Select()
        }
