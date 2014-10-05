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

__all__ = ('DataTree',)

"""
    DataTree models kept for data storage; functionality removed.
"""

class DataTree(models.Model):

    lock_choices = (
        (0, "UNLOCKED"),
        (1, "SOFT LOCK"),
        (2, "HARD LOCK"),
    )

    # some fields
    name          = models.CharField(max_length=64)
    friendly_name = models.TextField()
    parent        = AjaxForeignKey('self',blank=True,null=True, related_name='child_set')
    rangestart    = models.IntegerField(editable = False)
    rangeend      = models.IntegerField(editable = False)
    uri           = models.CharField(editable = False, max_length=1024)
    #^ a charfield for indexing purposes
    uri_correct   = models.BooleanField(editable = False, default = False)
    lock_table    = models.IntegerField(editable = False, default = 0,
                                        choices  = lock_choices)
    range_correct = models.BooleanField(editable = False, default = True )

    class Meta:
        # parent and name should be unique
        unique_together = (("name", "parent"),)
        # ordering should be by rangestart
        #ordering = ['rangestart','-rangeend']

    class Admin:
        ordering = ('rangestart', '-rangeend')

    def delete(self, recurse = False, superdelete = False):
        raise Exception('Attempted to delete a DataTree')

    def save(self, create_root=False, uri_fix=False, old_save=False, start_size=None, *args, **kwargs):
        raise Exception('Attempted to save a DataTree')

def GetNode(uri):
    #   This no longer creates on demand, so it should not be used in active code.
    return DataTree.objects.get(uri=uri)

def install():
    pass
