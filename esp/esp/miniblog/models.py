
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
from django.db import models
from markdown import markdown
from esp.users.models import ESPUser
from esp.db.fields import AjaxForeignKey
import datetime

# Create your models here.

class AnnouncementLink(models.Model):
    title = models.CharField(max_length=256)
    category = models.CharField(max_length=32) # Plaintext
    timestamp = models.DateTimeField(default=datetime.datetime.now, editable=False)
    highlight_begin = models.DateTimeField(blank=True,null=True, help_text="When this should start being showcased.")
    highlight_expire = models.DateTimeField(blank=True,null=True, help_text="When this should stop being showcased.")
    section = models.CharField(max_length=32,blank=True,null=True, help_text="e.g. 'teach' or 'learn' or blank")
    href = models.URLField(help_text="The URL the link should point to.")

    def __unicode__(self):
        return "%s (links to %s)" % (self.title, self.href)

    def get_absolute_url(self):
        return self.href
    makeUrl = get_absolute_url

    def makeTitle(self):
        return self.title

    def content(self):
        return '<a href="%s">Click Here</a> for details' % self.href

    def html(self):
        return '<p><a href="%s">%s</a></p>' % (self.href, self.title)

class Entry(models.Model):
    """ A Markdown-encoded miniblog entry """
    title = models.CharField(max_length=256) # Plaintext; shouldn't contain HTML, for security reasons, though HTML will probably be passed through intact
    slug    = models.SlugField(default="General",
                               help_text="(will determine the URL)")

    timestamp = models.DateTimeField(default = datetime.datetime.now, editable=False)
    highlight_begin = models.DateTimeField(blank=True,null=True,
                                            help_text="When this should start being showcased.")
    highlight_expire = models.DateTimeField(blank=True,null=True,
                                            help_text="When this should stop being showcased.")
    content = models.TextField(help_text='Yes, you can use markdown.') # Markdown-encoded
    sent    = models.BooleanField(editable=False, default=False)
    email   = models.BooleanField(editable=False, default=False)
    fromuser = AjaxForeignKey(ESPUser, blank=True, null=True,editable=False)
    fromemail = models.CharField(max_length=80, blank=True, null=True, editable=False)
    priority = models.IntegerField(blank=True, null=True) # Message priority (role of this field not yet well-defined -- aseering 8-10-2006)
    section = models.CharField(max_length=32,blank=True,null=True,help_text="e.g. 'teach' or 'learn' or blank")

    def __unicode__(self):
        if self.slug:
            return "%s" % (self.slug,)
        else:
            return "%s" % (self.title,)

    def html(self):
        return markdown(self.content)

    def makeTitle(self):
        return self.title

    class Meta:
        verbose_name_plural = 'Entries'
        ordering = ['-timestamp']

class Comment(models.Model):

    author = AjaxForeignKey(ESPUser)
    entry  = models.ForeignKey(Entry)

    post_ts = models.DateTimeField(default=datetime.datetime.now,
                                   editable=False)

    subject = models.CharField(max_length=256)

    content = models.TextField(help_text="HTML not allowed.")

    def __unicode__(self):
        return 'Comment for %s by %s on %s' % (self.entry, self.author,
                                               self.post_ts.date())

    class Meta:
        ordering = ['-post_ts']

# This import is necessary to prevent argcache errors
import esp.miniblog.views
