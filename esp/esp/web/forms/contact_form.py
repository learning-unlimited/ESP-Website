
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
from django.utils.translation import gettext_lazy as _

from django.conf import settings

person_type = (
    ('Student', 'K-12 Student'),
    ('Parent',  'Parent/Guardian'),
    ('Teacher', 'Teacher for ' + settings.ORGANIZATION_SHORT_NAME),
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
    sender  = forms.EmailField(label=_("Your Email"), required = True,
                               help_text=_("(e.g.: john.doe@domain.xyz)"))

    cc_myself = forms.BooleanField(label=_("Copy me"), required = False,
                                   help_text=_("(By checking this, we will send you a carbon-copy (cc) of this email.)") )

    name      = forms.CharField(max_length=100, label="Your Name", required=False)

    person_type  = forms.ChoiceField(choices = person_type, label=_("I am a(n)"))

    hear_about   = forms.ChoiceField(choices = hear_about, label="How did you hear about us?")
    topic   = forms.ChoiceField(choices = settings.CONTACTFORM_EMAIL_CHOICES, label=_("Topic"),
                                help_text = "(This determines who gets the message.)")

    subject = forms.CharField(max_length=100, label=_("Subject"))

    message = forms.CharField(label=_("Message"),
                              widget = forms.Textarea(attrs={'cols': 60,
                                                             'rows': 15,
                                                             'style': "width: 400px"}))

    # If this is true, then the user has seen and clicked through a message
    # checking whether they want to recover login information.
    decline_password_recovery = forms.BooleanField(required=False, widget=forms.HiddenInput)


