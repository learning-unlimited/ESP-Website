
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
from esp.utils.widgets import NavStructureWidget
from esp.middleware.threadlocalrequest import get_current_request

from django import forms
from django.conf import settings

class ConfigForm(ThemeConfigurationForm):
    titlebar_prefix = forms.CharField()
    full_group_name = forms.CharField()
    contact_info = forms.CharField(widget=forms.Textarea)
    nav_structure = forms.Field(widget=NavStructureWidget)
    # TODO(benkraft): Make all the contact info links fully editable, like the
    # navbar links.
    facebook_link = forms.URLField(required=False, help_text='Leave blank to omit a Facebook link.')
    # URLField requires an absolute URL, here we probably want relative.
    faq_link = forms.CharField(required=False, initial='/faq.html',
                               help_text='Leave blank to omit an FAQ link.')
    front_page_style = forms.ChoiceField(
                           choices=(('bubblesfront.html','Bubbles'),
                                    ('qsdfront.html','QSD')),
                           initial='qsdfront.html',
                           help_text='Choose the style of the front page of ' +
                           '<a href="%(home)s">%(host)s</a>. "Bubbles" is a ' +
                           # %(host)s is filled in by __init__()
                           'graphical landing page (see for example ' +
                           '<a href="https://esp.mit.edu">esp.mit.edu</a>), ' +
                           'and "QSD" is a standard page of editable ' +
                           'content (see for example ' +
                           '<a href="https://yale.learningu.org">yale.learningu.org</a>).')

    def __init__(self, *args, **kwargs):
        super(ConfigForm, self).__init__(*args, **kwargs)

        # fill in %(host)s for front_page_style.help_text
        request = get_current_request()
        if request is not None and 'HTTP_HOST' in request.META:
            host = request.META['HTTP_HOST']
        else:
            host = settings.SITE_INFO[1]
        self.fields['front_page_style'].help_text = \
            self.fields['front_page_style'].help_text % \
                {'home': '/', 'host': host}

