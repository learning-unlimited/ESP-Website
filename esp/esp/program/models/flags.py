__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2008 by the individual contributors
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

from esp.db.fields import AjaxForeignKey
from esp.middleware.threadlocalrequest import get_current_request
from argcache import cache_function

from esp.users.models import ESPUser
from esp.program.models import Program

class ClassFlagType(models.Model):
    name = models.CharField(max_length=255, unique=True)
    show_in_scheduler = models.BooleanField(default=False)
    show_in_dashboard = models.BooleanField(default=False)
    seq = models.SmallIntegerField(default=0, help_text='Flag types will be ordered by this.  Smaller is earlier; the default is 0.')
    color = models.CharField(blank=True, max_length=20, help_text='A color for displaying this flag type.  Should be a valid CSS color, for example "red", "#ff0000", or "rgb(255, 0, 0)".  If blank, an arbitrary one will be chosen.')

    class Meta:
        app_label='program'
        ordering=['seq']

    def __unicode__(self):
        return self.name

    def getColor(self):
        '''Get the display color for the flag type.'''
        if self.color:
            return self.color
        else:
            h = hash(self.name)
            r = 128 + h % 128
            g = 128 + (h // 128) % 16384
            b = 128 + (h // 16384) % 2097152
            # Choose a random one from the hash.
            return "#"+hex(r)[-2:]+hex(g)[-2:]+hex(b)[-2:]

    @cache_function
    def get_flag_types(cls, program=None, scheduler=False, dashboard=False):
        '''Gets all flag types associated with a given program, in a cached fashion.  If program is None, gets all flag types.  scheduler=True and dashboard=True return only flag types that should be shown in those interfaces.'''
        if program is None:
            base = cls.objects.all()
        else:
            base = program.flag_types.all()
        if scheduler:
            base = base.filter(show_in_scheduler=True)
        if dashboard:
            base = base.filter(show_in_dashboard=True)
        return base
    get_flag_types.depend_on_model('program.ClassFlagType')
    get_flag_types.depend_on_m2m('program.Program', 'flag_types', lambda prog, flag_type: {'program': prog})
    get_flag_types = classmethod(get_flag_types)

class ClassFlag(models.Model):
    subject = AjaxForeignKey('ClassSubject', related_name='flags')
    flag_type = models.ForeignKey(ClassFlagType)
    comment = models.TextField(blank=True)

    #The following will normally be set automagically, but if you create a Flag via the shell or a script, you will need to set them manually.
    modified_by = AjaxForeignKey(ESPUser, related_name='classflags_modified')
    modified_time = models.DateTimeField(auto_now=True)
    created_by = AjaxForeignKey(ESPUser, related_name='classflags_created')
    created_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label='program'
        ordering=['flag_type']


    def __unicode__(self):
        return "%s flag on %s: %s" % (self.flag_type, self.subject.emailcode(), self.subject.title)

    def save(self, *args, **kwargs):
        # Overridden to populate created_by and modified_by.  I'm not crazy about this method as it mixes models and requests, but I think it's worth it to save having to pass it around manually everywhere the thing gets touched.  Note that the creation and modification times already get autocreated by django.  If you're saving ClassFlags outside of a request somehow, make sure you manually populate this stuff.
        request = get_current_request()
        if request is not None:
            self.modified_by = request.user
            if self.id is None:
                #We are creating, rather than modifying, so we don't yet have an id.
                self.created_by = request.user
        super(ClassFlag, self).save(*args, **kwargs)

