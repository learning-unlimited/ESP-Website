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
from datetime import datetime
import hashlib

from django.db import models
from django.core.cache import cache
from django.contrib.auth.models import User

from esp.lib.markdown import markdown
from esp.db.fields import AjaxForeignKey
from esp.db.file_db import *
from esp.cache import cache_function
from esp.web.models import NavBarCategory
from esp.users.models import ESPUser

class QSDManager(FileDBManager):

    @cache_function
    def get_by_url(self, url):
        #Besides caching, this also handles finding the latest easily, 
        # and returning none when there isn't any such QSD
        #comment from an older version of this function:
        #    aseering 11-15-2009 -- Punt FileDB for this purpose;
        #    it has consistency issues in multi-computer load-balanced setups,
        #    and memcached doesn't have a clear performance disadvantage.
        try:
            return self.filter(url=url).select_related().latest('create_date')
        except QuasiStaticData.DoesNotExist:
            return None
    get_by_url.depend_on_row(lambda:QuasiStaticData, lambda qsd: {'url': qsd.url})

    def __str__(self):
        return "QSDManager()"

    def __repr__(self):
        return "QSDManager()"

class QuasiStaticData(models.Model):
    """ A Markdown-encoded web page """

    objects = QSDManager(8, 'QuasiStaticData')

    url = models.CharField(max_length=256, help_text="Full url, without the trailing .html")
    name = models.SlugField(blank=True)
    title = models.CharField(max_length=256)
    content = models.TextField()
    
    nav_category = models.ForeignKey(NavBarCategory, default=NavBarCategory.default)

    create_date = models.DateTimeField(default=datetime.now, editable=False)
    author = AjaxForeignKey(ESPUser)
    disabled = models.BooleanField(default=False)
    keywords = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def get_file_id(self):
        """Get the file_id of the object.

        This is used by the FileDBManager as a cache key, so be careful when updating.
        Changes here *may* cause caching to break in annoying ways elsewhere. We
        recommend grepping through any related files for "cache".
        
        In particular, IF you change this, update qsd/models.py's QSDManager class
        Otherwise, the cache *may* be used wrong elsewhere."""
        return qsd_cache_key(self.url, None) # DB access cache --- user invariant

    def copy(self,):
        """Returns a copy of the current QSD.

        This could be used for versioning QSDs, for example. It will not be
        saved to the DB until .save is called.
        
        Note that this method maintains the author and created date.
        Client code should probably reset the author to request.user
        and date to datetime.now (possibly with load_cur_user_time)"""
        qsd_new = QuasiStaticData()
        qsd_new.url    = self.url
        qsd_new.author  = self.author
        qsd_new.content = self.content
        qsd_new.title   = self.title
        qsd_new.description  = self.description
        qsd_new.nav_category = self.nav_category
        qsd_new.keywords     = self.keywords
        qsd_new.disabled     = self.disabled
        qsd_new.create_date  = self.create_date
        return qsd_new

    def load_cur_user_time(self, request, ):
        self.author = request.user
        self.create_date = datetime.now()

            
    def __unicode__(self):
        return self.url

    @cache_function
    def html(self):
        return markdown(self.content)
    html.depend_on_row(lambda:QuasiStaticData, 'self')

    @staticmethod
    def prog_qsd_url(prog, name):
        """Return the url for a program-qsd with given name
        
        Will have .html at the end iff name does"""
        parts = name.split(":")
        if len(parts)>1:
            return "/".join([parts[0], prog.url, ":".join(parts[1:])])
        else:
            return "/".join(["programs", prog.url, name])

def qsd_cache_key(path, user=None,):
    # IF you change this, update qsd/models.py's QSDManager class
    # Otherwise, the wrong cache path will be invalidated
    # Also, make sure the qsd/models.py's get_file_id method
    # is also updated. Otherwise, other things might break.
    if user and user.is_authenticated():
        return hashlib.md5('%s-%s' % (path, name, user.id)).hexdigest()
    else:
        return hashlib.md5('%s' % (path, ) ).hexdigest()


class ESPQuotations(models.Model):
    """ Quotation about ESP """

    content = models.TextField()
    display = models.BooleanField()
    author  = models.CharField(max_length=64)
    create_date = models.DateTimeField(default=datetime.now())

    @staticmethod
    def getQuotation():
        import random
        cutoff = .9
        if random.random() > cutoff:
            return None

        current_pool = cache.get('esp_quotes')

        if current_pool is None:
            current_pool = list(ESPQuotations.objects.filter(display=True).order_by('?')[:5])
            # Cache the current pool for a day
            if len(current_pool) == 0:
                return None

            cache.set('esp_quotes', current_pool, 86400)

        return random.choice(current_pool)

        
    class Meta:
        verbose_name_plural = 'ESP Quotations'

