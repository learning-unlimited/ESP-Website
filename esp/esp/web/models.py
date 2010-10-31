
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
from django.db.models.query import Q
from esp.datatree.models import *
from esp.lib.markdown import markdown
from esp.users.models import UserBit
from esp.db.fields import AjaxForeignKey  
        
# Create your models here.

class NavBarCategory(models.Model):
    anchor = AjaxForeignKey(DataTree, blank=True, null=True)
    include_auto_links = models.BooleanField()
    name = models.CharField(max_length=64)
    long_explanation = models.TextField()

    def get_navbars(self):
        return self.navbarentry_set.all().select_related('category').order_by('sort_rank')
    
    @classmethod
    def default(cls):
        """ Default navigation category.  For now, the one with the lowest ID. """
        if not hasattr(cls, '_default'):
            cls._default = cls.objects.all().order_by('id')[0]
        return cls._default
    
    def __unicode__(self):
        if self.anchor:
            return u'%s at %s' % (self.name, unicode(self.anchor))
        else:
            return u'%s' % self.name

class NavBarEntry(models.Model):
    """ An entry for the secondary navigation bar """
    
    #   ONLY the program related nav bars (i.e. "Splash Registration pages") should be anchored.
    #   This is to allow automatically generated links to appear.
    path = AjaxForeignKey(DataTree, related_name = 'navbar', blank=True, null=True)
    
    sort_rank = models.IntegerField()
    link = models.CharField(max_length=256, blank=True, null=True)
    text = models.CharField(max_length=64)
    indent = models.BooleanField()

    category = models.ForeignKey(NavBarCategory, default=NavBarCategory.default)

    def can_edit(self, user):
        return UserBit.UserHasPerms(user, self.path, GetNode('V/Administer/Edit/QSD'))
    
    def __unicode__(self):
        return unicode(self.category) + ':' + str(self.sort_rank) + ' (' + self.text + ') ' + '[' + self.link + ']' 

    def makeTitle(self):
        return self.text

    def makeUrl(self):
        return self.link
    
    def is_link(self):
        return (self.link is not None) and (len(self.link) > 0)
    
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
        return NavBarEntry.objects.filter(QTree(path__above =branch)).order_by('sort_rank')


def install():
    # Add a default nav bar category, to let QSD editing work.
    NavBarCategory.objects.get_or_create(name='default', defaults={ 'long_explanation':
        'The default category, to which new nav bars and QSD pages get assigned.'})
