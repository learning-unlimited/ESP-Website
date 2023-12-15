
from __future__ import absolute_import
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


from esp.themes.forms import ThemeConfigurationForm
from esp.utils.widgets import ContactFieldsWidget
from esp.utils.widgets import NavStructureWidget

from django import forms

class ConfigForm(ThemeConfigurationForm):
    title_text = forms.CharField()
    subtitle_text = forms.CharField()
    titlebar_prefix = forms.CharField()
    show_email = forms.BooleanField(required = False, help_text='Should the group email address be shown in the footer?')
    contact_links = forms.Field(required = False, widget=ContactFieldsWidget,
                                label='Contact links below contact info (use absolute or relative URLs)',
                                initial=[{"text": "contact us", "link": "/contact.html"}])
    nav_structure = forms.Field(widget=NavStructureWidget)
    facebook_link = forms.URLField(required=False, help_text='Leave blank to omit a Facebook link.')
    # URLField requires an absolute URL, here we probably want relative.
    faq_link = forms.CharField(required=False, initial='/faq.html',
                               help_text='Leave blank to omit an FAQ link.')
