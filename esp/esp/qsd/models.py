
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
from esp.datatree.models import *
from esp.lib.markdown import markdown
from django.contrib.auth.models import User
from django.core.cache import cache
from datetime import datetime
import hashlib

from esp.db.fields import AjaxForeignKey
from esp.db.file_db import *

class QSDManager(FileDBManager):
    def get_by_path__name(self, path, name):
        # This writes to file_db, and caches the *data retrieval*
        # It exists because the kernel filesystem caches are possibly better
        # for retrieving large (>=4KB) data chunks than PostgreSQL
        # See Mike Axiak's email to esp-webmasters@mit.edu on 2008-09-27 (around 12:35)
        # No user ID --- this caches simple DB access, so user-invariant
        file_id = qsd_cache_key(path, name, None)
        retVal = self.get_by_id(file_id)
        if retVal is not None:
            return retVal
        try:
            obj = self.filter(path=path, name=name).order_by('-create_date')[:1][0]
            self.obj_to_file(obj)
            return obj
        except IndexError:
            raise QuasiStaticData.DoesNotExist("No QSD found.")

class QuasiStaticData(models.Model):
    """ A Markdown-encoded web page """

    objects = QSDManager(8, 'QuasiStaticData')

    path = AjaxForeignKey(DataTree)
    name = models.SlugField()
    title = models.CharField(max_length=256)
    content = models.TextField()

    create_date = models.DateTimeField(default=datetime.now, editable=False)
    author = AjaxForeignKey(User)
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
        return qsd_cache_key(self.path, self.name, None) # DB access cache --- user invariant

    def copy(self,):
        """Returns a copy of the current QSD.

        This could be used for versioning QSDs, for example. It will not be
        saved to the DB until .save is called.
        
        Note that this method maintains the author and created date.
        Client code should probably reset the author to request.user
        and date to datetime.now (possibly with load_cur_user_time)"""
        qsd_new = QuasiStaticData()
        qsd_new.path    = self.path
        qsd_new.name    = self.name
        qsd_new.author  = self.author
        qsd_new.content = self.content
        qsd_new.title   = self.title
        qsd_new.description  = self.description
        qsd_new.keywords     = self.keywords
        qsd_new.disabled     = self.disabled
        qsd_new.create_date  = self.create_date
        return qsd_new

    def load_cur_user_time(self, request, ):
        self.author = request.user
        self.create_date = datetime.now()

    def save(self, user=None, *args, **kwargs):
        # Invalidate the file cache of the render_qsd template tag
        from esp.qsd.templatetags.render_qsd import cache_key as cache_key_func, render_qsd_cache
        render_qsd_cache.delete(cache_key_func(self))

        # Invalidate per user cache entry --- really, we should do this for
        # all users, but just this one is easy and almost as good
        render_qsd_cache.delete(cache_key_func(self, user))

        retVal = super(QuasiStaticData, self).save(*args, **kwargs)
        QuasiStaticData.objects.obj_to_file(self)
        
        # Invalidate the memory / Django cache
        from django.core.cache import cache
        cache_key = 'QSD_URL_%d' % self.id
        cache.delete(cache_key)
        
        return retVal

    def url(self):
        """ Get the relative URL of a page (i.e. /learn/Splash/eligibility.html) """
        from django.core.cache import cache
        cache_key = 'QSD_URL_%d' % self.id
        result = cache.get(cache_key)
        if result:
            return result
        
        my_path = self.path
        path_parts = self.path.get_uri().split('/')
        program_top = DataTree.get_by_uri('Q/Programs')
        web_top = DataTree.get_by_uri('Q/Web')
        if my_path.is_descendant_of(program_top):
            name_parts = self.name.split(':')
            if len(name_parts) > 1:
                result =  '/' + name_parts[0] + '/' + '/'.join(path_parts[2:]) + '/' + name_parts[1] + '.html'
            else:
                result = '/programs/' + '/'.join(path_parts[2:]) + '/' + name_parts[0] + '.html'
        elif my_path.is_descendant_of(web_top):
            result = '/' + '/'.join(path_parts[2:]) + '/' + self.name + '.html'
        else:
            result = '/' + '/'.join(path_parts[1:]) + '/' + self.name + '.html'
        
        cache.set(cache_key, result)
        return result
            
    def __unicode__(self):
        return (self.path.full_name() + ':' + self.name + '.html' )

    def html(self):
        return markdown(self.content)

    @staticmethod
    def find_by_url_parts(base, parts):
        """ Fetch a QSD record by its url parts """
        # Extract the last part
        filename = parts.pop()
        
        # Find the branch
        try:
            branch = base.tree_decode( parts )
        except DataTree.NoSuchNodeException:
            raise QuasiStaticData.DoesNotExist
        
        # Find the record
        qsd = QuasiStaticData.objects.filter( path = branch, name = filename )
        if len(qsd) < 1:
            raise QuasiStaticData.DoesNotExist
        
        # Operation Complete!
        return qsd[0]

def qsd_cache_key(path, name, user=None,):
    # IF you change this, update qsd/models.py's QSDManager class
    # Otherwise, the wrong cache path will be invalidated
    # Also, make sure the qsd/models.py's get_file_id method
    # is also updated. Otherwise, other things might break.
    if user and user.is_authenticated():
        return hashlib.md5('%s-%s-%s' % (path.uri, name, user.id)).hexdigest()
    else:
        return hashlib.md5('%s-%s' % (path.uri, name)).hexdigest()


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

