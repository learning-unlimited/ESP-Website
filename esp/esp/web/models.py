
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
from django.db.models.query import Q
from esp.datatree.models import DataTree, GetNode
from esp.lib.markdown import markdown
from esp.users.models import UserBit
from esp.db.fields import AjaxForeignKey
from esp.datatree.util import tree_filter_kwargs
        
# Create your models here.

class NavBarEntry(models.Model):
    """ An entry for the secondary navigation bar """
    path = AjaxForeignKey(DataTree, related_name = 'navbar')
    sort_rank = models.IntegerField()
    link = models.CharField(max_length=256)
    text = models.CharField(max_length=64)
    indent = models.BooleanField()
    section = models.CharField(max_length=64,blank=True)

    def can_edit(self, user):
        return UserBit.UserHasPerms(user, self.path, GetNode('V/Administer/Edit/QSD'))
    
    def __unicode__(self):
        return self.path.full_name() + ':' + self.section + ':' + str(self.sort_rank) + ' (' + self.text + ') ' + '[' + self.link + ']' 

    def makeTitle(self):
        return self.text

    def makeUrl(self):
        return self.link
    
    class Meta:
        verbose_name_plural = 'Nav Bar Entries'

    def save(self, *args, **kwargs):
        from django.core.cache import cache

        super(NavBarEntry, self).save(*args, **kwargs)
        
        cache.delete('LEFTBAR')

    
    @staticmethod
    def find_by_url_parts(parts):
        """ Fetch a QuerySet of NavBarEntry objects by the url parts """
        # Get the Q_Web root
        Q_Web = GetNode('Q/Web')
        
        # Remove the last component
        parts.pop()
        
        # Find the branch
        try:
            branch = Q_Web.tree_decode( parts )
        except DataTree.NoSuchNodeException, ex:
            branch = ex.anchor
            if branch is None:
                raise NavBarEntry.DoesNotExist
            
        # Find the valid entries
        return NavBarEntry.objects.filter(**tree_filter_kwargs(path__above = branch)).order_by('sort_rank')

