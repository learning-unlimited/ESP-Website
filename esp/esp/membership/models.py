
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

from django.db import models
from esp.program.models import ContactInfo
import datetime

attend_status_choices = (
    ('With certainty', 'With certainty'),
    ('Probably', 'Probably'),
    ('Possibly', 'Possibly'),
    ('No','No'),
    )

class AlumniContact(models.Model):
    """ This model answers the following questions: 
    1. If you were not part of ESP, please let us know (check box)
    2. I was part of ESP from [box for year] until [box for year]
    3. I was involved in: (check box list of all programs we know of, and then an
    'other' options)
    4. Can we make the above information available to other alumni? (check box)
    5. Contact information boxes for address, email, and phone
    6. Are you able to attend ESP's landmark 50th anniversary celebration on
    Saturday, September 14th?
    7. Would you like to get involved with ESP again by:
    a. receiving our biannual e-newsletter updating you on our current activities
    b. becoming part of an alumni advising email list
    c. volunteering for current programs
    8. To find out a little bit more about what we are up to check out [Link to a
    blurb written specifically for them]
    9. Any more information they'd like to provide. (blank box) 
    """
    partofesp = models.BooleanField('Were you a part of ESP?  If so, continue below')
    start_year = models.IntegerField('From year',blank=True,null=True)
    end_year = models.IntegerField('To year',blank=True,null=True)
    involvement = models.TextField('What ESP programs/activities were you involved with?',blank=True,null=True)
    contactinfo = models.ForeignKey(ContactInfo, blank=True, related_name='alumni_user', verbose_name='Contact Information')
    attend_interest = models.CharField('I am able to attend ESP\'s 50th anniversary event', choices=attend_status_choices, maxlength=50)
    news_interest = models.BooleanField('Send me a biannual e-mail newsletter')
    advising_interest = models.BooleanField('Join our alumni advising e-mail list')
    volunteer_interest = models.BooleanField('I would like to volunteer at current ESP programs')
    comments = models.TextField('What else do you have to tell us?  What questions do you have?', blank=True,null=True)

    create_ts = models.DateTimeField(default=datetime.datetime.now,
                                     editable=False)
    
    class Admin:
        pass
