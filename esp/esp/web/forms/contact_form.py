
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

from django import forms
from django.utils.translation import gettext_lazy as _
email_choices = (
    ('esp','Unknown'),
    ('general','General ESP'),
    ('esp-web','Web Site Problems'),
    ('satprep','SATPrep'),
    ('splash','Splash!'),
    ('hssp', 'HSSP'),
    ('junction', 'Junction'),
    ('delve',    'Delve'),
    ('splashonwheels', 'Splash On Wheels'),
    ('proveit',        'ProveIt'),
    ('membership',     'Student Reps'),
    ('relations',  'K-12 School Relations'),
    ('mit',        'MIT Relations'),    
    
    )

# corresponding email addresses
email_addresses = {
    'esp'     : 'esp@mit.edu',
    'general'     : 'esp@mit.edu',    
    'esp-web' : 'web@esp.mit.edu',
    'satprep' : 'satprep-director@mit.edu',
    'splash'  : 'esp@mit.edu',
    'hssp'    : 'hssp-director@mit.edu',
    'junction': 'junction-director@mit.edu',
    'splashonwheels': 'splash-on-wheels@mit.edu',
    'proveit' : 'proveit-director@mit.edu',
    'relations': 'esp@mit.edu',
    'mit'      : 'esp-publicity@mit.edu',
    'membership': 'esp-membership@mit.edu',
    'delve'    : 'delve-director@mit.edu',

    }

# if the picked email address isn't in the above, it will send to this.
fallback_address = 'esp@mit.edu'

person_type = (
    ('Student', 'K-12 Student'),
    ('Parent',  'Parent/Guardian'),
    ('Teacher', 'Teacher for ESP'),
    ('K-12 Educator', 'K-12 Educator'),
    ('Other',   'Other'),
    )

hear_about = (
    ('School', 'School'),
    ('Posters', 'Posters'),
    ('Friend','Friend'),
    ('Website','Website'),
    ('Referral', 'Referral'),
    ('Other', 'Other'),
    )

class ContactForm(forms.Form):
    sender  = forms.EmailField(label=_("Your Email"), required = False,
                               help_text=_("(e.g.: john.doe@domain.xyz)"))
    
    cc_myself = forms.BooleanField(label=_("Copy me"), required = False,
                                   help_text=_("(By checking this, we will send you a carbon-copy (cc) of this email.)") )

    name      = forms.CharField(max_length=100, label="Your Name", required=False)

    person_type  = forms.ChoiceField(choices = person_type, label=_("I am a(n)"))

    hear_about   = forms.ChoiceField(choices = hear_about, label="How did you hear about us?")
    topic   = forms.ChoiceField(choices = email_choices, label=_("Topic"),
                                help_text = "(This determines who gets the message.)")
    

    

    subject = forms.CharField(max_length=100, label=_("Subject"))

    message = forms.CharField(label=_("Message"),
                              widget = forms.Textarea(attrs={'cols': 60,
                                                             'rows': 15,
                                                             'style': "width: 400px"}))



    
