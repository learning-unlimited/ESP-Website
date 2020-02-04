__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2011 by the individual contributors
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
from esp.utils.forms import SizedCharField, FormWithRequiredCss, FormUnrestrictedOtherUser

class StanfordTeacherQuestionsForm(FormWithRequiredCss):
    schedule_acknowledgement = forms.BooleanField(label='Acknowledgement', help_text='Splash will be on Halloween weekend (Oct. 29-30)!  Please acknowledge that you are aware of this and commit to teaching at one of the times you have specified for your availability.')

class BCTeacherQuestionsForm(FormWithRequiredCss):
    qualifications = forms.CharField(label='Qualifications', help_text='What are your qualifications for teaching this course?', widget=forms.Textarea(attrs={'cols': 40, 'rows': 4}))
    computer_type = forms.CharField(label='Computer Type', help_text='If you are using a computer to project slides in your class, what kind of computer is it?')
    video_adapter = forms.ChoiceField(label='Video Adapter', help_text='If you have a Mac, do you have a VGA video adapter?', choices=[('yes', 'Yes'), ('no', 'No'), ('pc', 'N/A - I have a PC')])

class ChicagoTeacherQuestionsForm(FormWithRequiredCss):
    room_type = forms.ChoiceField(label='Room type', choices=[('discussion', 'Discussion style'), ('lecture', 'Lecture style'), ('large', 'Large open room'), ('kitchen', 'Kitchen'), ('outdoors', 'Outdoors'), ('other', 'Other (please explain)')])
    discussion_type = forms.ChoiceField(label='', choices=[('', ''), ('carpet', 'Carpeted'), ('nocarpet', 'Not carpeted'), ('dontcare', 'No preference')], help_text='Specify your room preference here if you selected "Large, open room" above.', required=False)
    other_explain = forms.CharField(label='', help_text='Explain here if you chose "Other" above.', required=False)
    dance_space = forms.BooleanField(label='',help_text='Please select this box if you would like a dance space with a barre.  We cannot guarantee that we will have enough of these rooms to meet demands, but we will work with you to find a room that will allow you teach an amazing class!', required=False)
    std_equipment = forms.MultipleChoiceField(label='Standard equipment requests', choices=[('audio', 'Audio support'), ('video', 'Visual support'), ('macadapter', 'Mac Adapter')], widget=forms.CheckboxSelectMultiple, required=False)
    mac_adapter = forms.CharField(label='', help_text='If you have a Mac and know what kind of adapter you need, please write it in here.  Otherwise, leave this blank.', required=False)
    special_equipment = forms.CharField(label='Special equipment requests', widget=forms.Textarea(attrs={'rows':4}), required=False,
                                         help_text='If you plan to purchase anything for your class, please indicate here what you plan to purchase and how much it will cost. Please talk with the program directors first before buying materials for your class!')
    additional_comments = forms.CharField(label='Message for Directors', widget=forms.Textarea(attrs={'rows':4}), required=False,
                                                   help_text='Are there any special circumstances you\'d like us to know about?' )
