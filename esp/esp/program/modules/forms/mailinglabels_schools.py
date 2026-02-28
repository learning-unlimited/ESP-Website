"""
  Form for Selecting schools for mailing labels
"""

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


class SchoolSelectForm(forms.Form):

    proximity = forms.CharField(max_length=4,
                                label = 'Distance from zip code below.',
                                help_text = 'Maximum distance. E.g. 50 for 50 miles.')

    zip_code = forms.CharField(max_length=5,
                               label='Center of the circle to find schools.',
                               help_text = 'Standard 5-digit zip code. E.g. &quot;02139&quot;.')


    grades = forms.CharField(max_length=100,
                             help_text = 'List of grades separated by commas. E.g. &quot;4,8,10&quot;',
                             label = "Grades")

    grades_exclude = forms.CharField(max_length=100, required=False,
                             help_text = 'List of grades separated by commas. E.g. &quot;4,8,10&quot;',
                             label = "Grades to exclude")

    combine_addresses = forms.BooleanField(label = 'Combine Like Addresses', required = False,
                                            help_text = 'Take similar addresses and combine them.')
