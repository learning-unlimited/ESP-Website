
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

from esp.membership.models import AlumniContact
from esp.users.models import ContactInfo
from esp.utils.forms import new_callback, grouped_as_table, add_fields_to_class
from esp.membership.models import attend_status_choices, partofesp_choices
from django import newforms as forms

#   Modify the CharField class to support our formatting features.
add_fields_to_class(forms.CharField, {'is_long': False, 'line_group': 0})


class ContactInfoForm(forms.form_for_model(ContactInfo, formfield_callback=new_callback(exclude=['phone_cell', 'phone_even', 'phone_day', 'user', 'address_postal', 'undeliverable']))):
    """
    This represents a standard pretty contact info form that can be used in a multitude of places.
    """
    
    def __init__(self, *args, **kwargs):
        self.base_fields['address_city'].line_group = 1
        self.base_fields['address_state'].line_group = 1
        self.base_fields['address_zip'].line_group = 1
        super(ContactInfoForm, self).__init__(*args, **kwargs)

    # use field grouping
    as_table = grouped_as_table

class AlumniContactForm(forms.form_for_model(AlumniContact, formfield_callback=new_callback(exclude=['contactinfo', 'involvement', 'news_interest', 'volunteer_interest', 'reconnect_interest', 'advising_interest']))):
    """
    This is an alumni contact form which is used to get information from alumni of ESP.
    """
    def __init__(self, *args, **kwargs):
        self.base_fields['comments'].is_long = True
        #   self.base_fields['involvement'].is_long = True
        self.base_fields['start_year'].line_group = -1
        self.base_fields['end_year'].line_group = -1
        self.base_fields['partofesp'] = \
                forms.ChoiceField(choices = partofesp_choices,
                    label = AlumniContact._meta.get_field('partofesp').verbose_name)
        self.base_fields['partofesp'].line_group = -2
        self.base_fields['attend_interest'] = \
                forms.ChoiceField(choices = attend_status_choices,
                                  label = AlumniContact._meta.get_field('attend_interest').verbose_name)
        super(AlumniContactForm, self).__init__(*args, **kwargs)

    # use field grouping
    as_table = grouped_as_table
