
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
from django.db.models.query import Q

from esp.datatree.models import DataTree
from esp.db.fields import AjaxForeignKey
from esp.cache import cache_function
        
class NavBarCategory(models.Model):
    anchor = AjaxForeignKey(DataTree, blank=True, null=True)
    include_auto_links = models.BooleanField()
    name = models.CharField(max_length=64)
    path = models.CharField(max_length=64, default='', help_text='Matches the beginning of the URL (without the /).  Example: learn/splash')
    long_explanation = models.TextField()

    def get_navbars(self):
        return self.navbarentry_set.all().select_related('category').order_by('sort_rank')
    
    @cache_function
    def from_request(section, path):
        """ A function to guess the appropriate navigation category when one
            is not provided in the context. """

        if path:
            #   See if there's a category whose path matches the desired URL.
            categories = NavBarCategory.objects.extra(select={'length':'Length(path)'}).order_by('-length')
            for cat in categories:
                if cat.path and path.lower().startswith(cat.path.lower()):
                    return cat

        if section:
            #   See if there's a category whose name matches the desired section.
            categories = NavBarCategory.objects.filter(name=section)
            if categories.count() > 0:
                return categories[0]

        #   If all else fails, make something up.
        return NavBarCategory.default()

    from_request.depend_on_model('web.NavBarCategory')
    from_request = staticmethod(from_request)
    
    @classmethod
    def default(cls):
        """ Default navigation category.  For now, the one with the lowest ID. """
        if not hasattr(cls, '_default'):
            if not cls.objects.exists():
                install()
            cls._default = cls.objects.all().order_by('id')[0]
        return cls._default
    
    def __unicode__(self):
        return u'%s' % self.name

class NavBarEntry(models.Model):
    """ An entry for the secondary navigation bar """

    path = AjaxForeignKey(DataTree, related_name = 'navbar', blank=True, null=True)
    
    sort_rank = models.IntegerField()
    link = models.CharField(max_length=256, blank=True, null=True)
    text = models.CharField(max_length=64)
    indent = models.BooleanField()

    category = models.ForeignKey(NavBarCategory, default=NavBarCategory.default)

    def can_edit(self, user):
        return user.isAdmin()
    
    def __unicode__(self):
        return u'%s:%s (%s) [%s]' % (self.category, self.sort_rank, self.text, self.link)

    def makeTitle(self):
        return self.text

    def makeUrl(self):
        return self.link
    
    def is_link(self):
        return (self.link is not None) and (len(self.link) > 0)
    
    class Meta:
        verbose_name_plural = 'Nav Bar Entries'

def install():
    # Add a default nav bar category, to let QSD editing work.
    print "Installing esp.web initial data..."
    if not NavBarCategory.objects.filter(name='default').exists():
        NavBarCategory.objects.create(
            name='default',
            long_explanation='The default category, to which new nav bars and QSD pages get assigned.',
        )
