
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
from esp.db.models import Q
from esp.datatree.models import DataTree, GetNode
from esp.lib.markdown import markdown
from esp.users.models import UserBit
from esp.dbmail.models import MessageRequest
from django.contrib.auth.models import User
from esp.db.fields import AjaxForeignKey
from django.core.cache import cache
import datetime

# Create your models here.

class Entry(models.Model):
    """ A Markdown-encoded miniblog entry """
    anchor = AjaxForeignKey(DataTree)
    title = models.CharField(maxlength=256) # Plaintext; shouldn't contain HTML, for security reasons, though HTML will probably be passed through intact
    slug    = models.SlugField(prepopulate_from=('title',),
                               help_text="(will determine the URL)")

    timestamp = models.DateTimeField(default = datetime.datetime.now, editable=False)
    highlight_expire = models.DateTimeField(blank=True,null=True,
                                            help_text="When this should stop being showcased.")
    content = models.TextField(help_text='Yes, you can use markdown.') # Markdown-encoded
    sent    = models.BooleanField(editable=False, default=False)
    email   = models.BooleanField(editable=False, default=False)
    fromuser = AjaxForeignKey(User, blank=True, null=True,editable=False)
    fromemail = models.CharField(maxlength=80, blank=True, null=True, editable=False)
    priority = models.IntegerField(blank=True, null=True) # Message priority (role of this field not yet well-defined -- aseering 8-10-2006)
    section = models.CharField(maxlength=32,blank=True,null=True,help_text="e.g. 'teach' or 'learn' or blank")

    def __str__(self):
        if self.slug:
            return "%s (%s)" % (self.slug, self.anchor.uri)
        else:
            return "%s (%s)" % (self.title, self.anchor.uri)

    def html(self):
        return markdown(self.content)

    def makeTitle(self):
        return self.title

    def makeUrl(self):
        return "/blog/"+str(self.id)+"/"
    
    @staticmethod
    def find_posts_by_perms(user, verb, qsc=None):
        """ Fetch a list of relevant posts for a given user and verb """
        if qsc==None:
            return UserBit.find_by_anchor_perms(Entry,user,verb)
        else:
            return UserBit.find_by_anchor_perms(Entry,user,verb,qsc=qsc)

    class Admin:
        search_fields = ['content','title','anchor__uri']
        js = (
            '/media/scripts/admin_miniblog.js',
            )

    @staticmethod
    def post( user_from, anchor, subject, content, email=False, user_email = ''):
        newentry = Entry()
        newentry.content = content
        newentry.title = subject
        newentry.anchor = anchor
        newentry.email  = email
        newentry.sent  = False
        newentry.fromuser = user_from
        newentry.fromemail = user_email
        newentry.save()

        return newentry

    def subscribe_user(self, user):
        verb = GetNode('V/Subscribe')
        from esp.users.models import ESPUser, User
        if type(user) != User and type(user) != ESPUser:
            assert False, 'EXPECTED USER, received %s' \
                     % str(type(user))
        ub = UserBit.objects.filter(verb = verb,
                        qsc  = self.anchor,
                        user = user)

        if ub.count() > 0:
            return False

        ub = UserBit(verb = verb,
                 qsc  = self.anchor,
                 user = user
                 )
        ub.save()
        return True

    def get_absolute_url(self):
        if hasattr(self, '_url'):
            return self._url
        
        directory = ('/'+'/'.join(self.anchor.get_uri().split('/')[2:])).strip('/')

        self._url = '%s/%s.blog' % (directory, self.slug)

        return self._url


    def save(self, *args, **kwargs):
        cache.delete('BLOG_DISPLAY__%s' % self.id)
        super(Entry, self).save(*args, **kwargs)
    
    class Meta:
        unique_together = (('slug','anchor',),)
        verbose_name_plural = 'Entries'
        ordering = ['-timestamp']
    

class Comment(models.Model):

    author = AjaxForeignKey(User)
    entry  = models.ForeignKey(Entry)
    
    post_ts = models.DateTimeField(default=datetime.datetime.now,
                                   editable=False)

    subject = models.CharField(maxlength=256)

    content = models.TextField(help_text="HTML not allowed.")

    def __str__(self):
        return 'Comment for %s by %s at %s' % (self.entry, self.author,
                                               self.get_absolute_url())
    
    class Admin:
        search_fields = ['author__first_name','author__last_name',
                         'subject','entry__title']

    class Meta:
        ordering = ['-post_ts']
        

