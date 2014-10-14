__author__    = "$LastChangedBy$"
__date__      = "$LastChangedDate$"
__rev__       = "$LastChangedRevision$"
__headurl__   = "$HeadURL$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2013 by the individual contributors
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
from esp.users.models import ESPUser
from esp.datatree.models import *
import datetime

__all__ = ['UserBit','UserBitImplication']

"""
    UserBit models kept for data storage; functionality removed.
"""

class UserBit(models.Model):

    user = AjaxForeignKey(ESPUser, 'id', blank=True, null=True, default=None) # User to give this permission
    qsc = AjaxForeignKey(DataTree, related_name='userbit_qsc') # Controller to grant access to
    verb = AjaxForeignKey(DataTree, related_name='userbit_verb') # Do we want to use Subjects?

    startdate = models.DateTimeField(blank=True, default = datetime.datetime.now)
    enddate = models.DateTimeField(blank=True, default = datetime.datetime(9999,1,1))
    recursive = models.BooleanField(default=True)

    class Meta:
        app_label = 'users'
        db_table = 'users_userbit'

    def delete(self, *args, **kwargs):
        raise Exception('Attempted to delete a UserBit')

    def save(self, *args, **kwargs):
        raise Exception('Attempted to save a UserBit')

    @staticmethod
    def valid_objects():
        now = datetime.datetime.now()
        return UserBit.objects.filter(startdate__lte=now, enddate__gte=now)

class UserBitImplication(models.Model):
    """ This model will create implications for userbits...
      that is, if a user has A permission, they will get B """
    
    qsc_original  = AjaxForeignKey(DataTree, related_name = 'qsc_original',  blank=True, null=True)
    verb_original = AjaxForeignKey(DataTree, related_name = 'verb_original', blank=True, null=True)
    qsc_implied   = AjaxForeignKey(DataTree, related_name = 'qsc_implied',   blank=True, null=True)
    verb_implied  = AjaxForeignKey(DataTree, related_name = 'verb_implied',  blank=True, null=True)
    recursive     = models.BooleanField(default = True)
    created_bits  = models.ManyToManyField(UserBit, blank=True, null=True)

    class Meta:
        app_label = 'users'
        db_table = 'users_userbitimplication'

    def delete(self, *args, **kwargs):
        raise Exception('Attempted to delete a UserBitImplication')

    def save(self, *args, **kwargs):
        raise Exception('Attempted to save a UserBitImplication')

