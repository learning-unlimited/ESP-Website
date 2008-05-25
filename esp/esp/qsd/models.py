
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
from esp.datatree.models import DataTree, GetNode
from esp.lib.markdown import markdown
from django.contrib.auth.models import User
from django.core.cache import cache
from datetime import datetime
import md5

from esp.db.fields import AjaxForeignKey
from esp.db.file_db import *

class QSDManager(FileDBManager):
    def get_by_path__name(self, path, name):
        file_id = md5.new(path.uri + '-' + name).hexdigest()
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
    title = models.CharField(maxlength=256)
    content = models.TextField()

    create_date = models.DateTimeField(default=datetime.now, editable=False)
    author = AjaxForeignKey(User)
    disabled = models.BooleanField(default=False)
    keywords = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def get_file_id(self):
        return md5.new(self.path.uri + '-' + self.name).hexdigest()

    def save(self, *args, **kwargs):
        from esp.qsd.templatetags.render_qsd import cache_key as cache_key_func, render_qsd_cache
        render_qsd_cache.delete(cache_key_func(self))
        retVal = super(QuasiStaticData, self).save(*args, **kwargs)
        QuasiStaticData.objects.obj_to_file(self)
        
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
        if (my_path.rangestart >= program_top.rangestart) and (my_path.rangeend <= program_top.rangeend):
            name_parts = self.name.split(':')
            if len(name_parts) > 1:
                result =  '/' + name_parts[0] + '/' + '/'.join(path_parts[2:]) + '/' + name_parts[1] + '.html'
            else:
                result = '/programs/' + '/'.join(path_parts[2:]) + '/' + name_parts[0] + '.html'
        elif (my_path.rangestart >= web_top.rangestart) and (my_path.rangeend <= web_top.rangeend):
            result = '/' + '/'.join(path_parts[2:]) + '/' + self.name + '.html'
        else:
            result = '/' + '/'.join(path_parts[1:]) + '/' + self.name + '.html'
        
        cache.set(cache_key, result)
        return result
            
    def __str__(self):
        return (self.path.full_name() + ':' + self.name + '.html' )

    class Admin:
        search_fields = ['title','name','keywords','description']

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


class ESPQuotations(models.Model):
    """ Quotation about ESP """

    content = models.TextField()
    display = models.BooleanField()
    author  = models.CharField(maxlength=64)
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


    class Admin:
        pass

