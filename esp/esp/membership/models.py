
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
  Email: web-team@lists.learningu.org
"""

from django.db import models
from esp.db.fields import AjaxForeignKey
from esp.datatree.models import *
from esp.program.models import ContactInfo
import datetime

rsvp_choices = (
    ('Yes', 'Yes'),
    ('No', 'No'),
    )
    
guest_choices = (
    ('0', '0'),
    ('1', '1'),
    ('2', '2'),
    ('3', '3'),
    )

class AlumniRSVP(models.Model):
    name = models.CharField('Your name', max_length=30)
    attending = models.CharField('Are you coming?', choices=rsvp_choices, max_length=10)
    num_guests = models.IntegerField('Number of guests', choices=guest_choices)
    comments = models.TextField('Questions or comments', null=True)   
     
    def __unicode__(self):
        if self.attending == 'Yes':
            return 'RSVP for %s: Attending with %s guests' % (self.name, self.num_guests)
        else:
            return 'RSVP for %s: Not Attending' % self.name
        
    class Admin:
        pass

class AlumniInfo(models.Model):
    start_year = models.IntegerField('From year',blank=True,null=True)
    end_year = models.IntegerField('To year',blank=True,null=True)
    involvement = models.TextField('What ESP programs/activities (HSSP, Splash, SAT Prep, etc.) were you involved with?',blank=True,null=True)
    
    news_interest = models.BooleanField('Would you like to receive our e-mail newsletter twice yearly?', default=False)
    advising_interest = models.BooleanField('Would you like to join an e-mail list of alumni that advise ESP?', default=False)
    
    contactinfo = AjaxForeignKey(ContactInfo, blank=True, related_name='alumni_user', verbose_name='Contact Information')
    
    def __unicode__(self):
        return "%s %s (%s-%s)" % (self.contactinfo.first_name, self.contactinfo.last_name, self.start_year, self.end_year)
        
    @classmethod
    def ajax_autocomplete(cls, data):
        names = data.strip().split(',')
        last = names[0]

        query_set = cls.objects.filter(contactinfo__last_name__istartswith = last.strip())

        if len(names) > 1:
            first  = ','.join(names[1:])
            if len(first.strip()) > 0:
                query_set = query_set.filter(contactinfo__first_name__istartswith = first.strip())

        values = query_set.select_related().order_by('start_year').values('id', 'start_year', 'end_year', 'contactinfo')

        for value in values:
            ci = ContactInfo.objects.get(id=value['contactinfo'])
            value['ajax_str'] = '%s, %s (%s-%s)' % (ci.last_name, ci.first_name, value['start_year'], value['end_year'])
        return values

    def ajax_str(self):
        return "%s, %s (%s-%s)" % (self.contactinfo.last_name, self.contactinfo.first_name, self.start_year, self.end_year)

    @staticmethod
    def lookup(data):
        """ Take the first_name, last_name, start_year, end_year fields and see if you can find people.
        Return a QuerySet of AlumniInfos. """
        def check_data_for_key(key):
            return data.has_key(key) and data[key] is not None

        qs = AlumniInfo.objects.all()
        if check_data_for_key('first_name'):
            qs = qs.filter(contactinfo__first_name__icontains=data['first_name'])
        if check_data_for_key('last_name'):
            qs = qs.filter(contactinfo__last_name__icontains=data['last_name'])
        
        if check_data_for_key('start_year') and check_data_for_key('end_year'):
            qs = qs.filter(start_year__lte=data['end_year'], end_year__gte=data['start_year'])
        elif check_data_for_key('start_year'):
            qs = qs.filter(start_year=data['start_year'])
        elif check_data_for_key('end_year'):
            qs = qs.filter(end_year=data['end_year'])
            
        return qs.order_by('start_year')
    
    class Admin:
        pass
    
    
class AlumniMessage(models.Model):
    #   A simple thread posting.
    poster = models.CharField('Who are you?', max_length=128)
    thread = models.ForeignKey('AlumniContact')
    seq = models.IntegerField()
    content = models.TextField('Message')
    
    TEMPLATE_FILE = 'membership/single_message.html'
    
    def __unicode__(self):
        return 'Post by %s (ref: %s)' % (self.poster, self.thread.comment)
    
    def html(self):
        from django.template import loader
        context = {'content': self.content, 'seq': self.seq, 'poster': self.poster}
        return loader.render_to_string(self.TEMPLATE_FILE, context)
    
    class Admin:
        pass
    
class AlumniContact(models.Model):
    #   An AlumniContact is like the start of a discussion thread consisting of AlumniMessages.
    participants = models.ManyToManyField(AlumniInfo, verbose_name='Select people to associate posting with')
    anchor = models.ForeignKey(DataTree, verbose_name='Program (if any) to associate posting with', null=True)
    year = models.IntegerField('Year[s]')
    timestamp = models.DateTimeField(default = datetime.datetime.now)
    comment = models.CharField('Post title/note', max_length=256, null=True)

    def __unicode__(self):
        return '%s (year: %s)' % (self.comment, self.year)

    def get_reply_form(self, request):
        from esp.membership.forms import AlumniMessageForm
        #   If the form is already there, don't mess with it.  
        #   Otherwise, come up with a blank one.
        if hasattr(self, 'reply_form'):
            return self.reply_form
        else:
            self.reply_form = AlumniMessageForm(thread=self, request=request)
            return self.reply_form

    def max_seq(self):
        messages = AlumniMessage.objects.filter(thread=self).order_by('-seq')
        if messages.count() > 0:
            return messages[0].seq
        else:
            return 0

    def messages(self):
        qs = AlumniMessage.objects.filter(thread=self).order_by('seq')
        return list(qs)
    
    class Admin:
        pass    
