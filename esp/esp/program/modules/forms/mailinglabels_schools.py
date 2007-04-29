"""
  Form for Selecting schools for mailing labels
"""

__author__    = "MIT ESP"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "GPL v.2"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 MIT ESP

The ESP Web Site is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

Contact Us:
ESP Web Group
MIT Educational Studies Program,
84 Massachusetts Ave W20-467, Cambridge, MA 02139
Phone: 617-253-4882
Email: web@esp.mit.edu
"""

from django import newforms as forms


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
