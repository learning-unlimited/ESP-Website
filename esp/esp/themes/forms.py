
__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2013 by the individual contributors
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

from esp.themes.controllers import ThemeController
from esp.tagdict.models import Tag

from django import forms

import json

class ThemeConfigurationForm(forms.Form):
    theme = forms.CharField(widget=forms.HiddenInput)
    just_selected = forms.NullBooleanField(widget=forms.HiddenInput, initial=False)

    def prepare_for_serialization(self, data):
        return data

    def recover_from_serialization(self, data):
        return data

    def save_to_tag(self):
        tc = ThemeController()
        data = self.prepare_for_serialization(self.cleaned_data.copy())
        tc.set_template_settings(data)

    @classmethod
    def load_from_tag(cls, theme_name=None, just_selected=False):
        data = json.loads(Tag.getTag('theme_template_control'))
        if theme_name is None:
            tc = ThemeController()
            theme_name = tc.get_current_theme()
        data['theme'] = theme_name
        form_temp = cls(initial=data)
        data = form_temp.recover_from_serialization(data)
        data['just_selected'] = just_selected
        form = cls(initial=data)
        return form

    @classmethod
    def initial_data(cls):
        """
        A dictionary of the initial values of the configuration form fields.
        """
        return dict(map(lambda (k,v): (k, v.initial), cls().fields.iteritems()))

