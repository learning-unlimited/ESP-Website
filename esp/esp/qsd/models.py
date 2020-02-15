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
from datetime import datetime
import hashlib

from django.db import models

from markdown import markdown
from esp.db.fields import AjaxForeignKey
from argcache import cache_function
from esp.web.models import NavBarCategory, default_navbarcategory
from esp.users.models import ESPUser

class QSDManager(models.Manager):

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
    get_by_url.depend_on_row('qsd.QuasiStaticData', lambda qsd: {'url': qsd.url})

    @cache_function
    def get_by_url_else_init(self, url, defaults={}):
        """
        Tries looking up a QSD object by url, using self.get_by_url(). If this
        fails because the url does not have a saved QSD object yet, initializes
        and returns a new QSD object, without saving it to the database.
        """
        qsd_obj = self.get_by_url(url)
        if qsd_obj is None:
            qsd_obj = QuasiStaticData(url=url, **defaults)
            # Because of the way templates are usually written, there will
            # often be unintended whitespace at the beginnings of lines of the
            # default content of an inline QSD. Usually a line starts with some
            # template indentation before the actual content. However, Markdown
            # will interpret this as a code block.  To avoid this, we assume
            # that the default content will never purposely use Markdown code
            # blocks, and we strip this unintended space.
            content = unicode(qsd_obj.content.lstrip())
            content = content.split('\n')
            content = map(unicode.lstrip, content)
            content = '\n'.join(content)
            qsd_obj.content = content
        return qsd_obj
    get_by_url_else_init.depend_on_row('qsd.QuasiStaticData', lambda qsd: {'url': qsd.url})

    def __str__(self):
        return "QSDManager()"

    def __repr__(self):
        return "QSDManager()"

def qsd_edit_id(val):
    """ A short hex string summarizing the QSD's URL. """
    return hashlib.sha1(val).hexdigest()[:8]

class QuasiStaticData(models.Model):
    """ A Markdown-encoded web page """

    objects = QSDManager()

    url = models.CharField(max_length=256, help_text="Full url, without the trailing .html")
    name = models.SlugField(blank=True)
    title = models.CharField(max_length=256)
    content = models.TextField()

    nav_category = models.ForeignKey(NavBarCategory, default=default_navbarcategory)

    create_date = models.DateTimeField(default=datetime.now, editable=False, verbose_name="last edited")
    author = AjaxForeignKey(ESPUser, verbose_name="last modifed by") #I believe that these are,uh, no longer descriptive names. This is silly, but the verbose names should fit better.
    disabled = models.BooleanField(default=False)
    keywords = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def edit_id(self):
        return qsd_edit_id(self.url)

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
    html.depend_on_row('qsd.QuasiStaticData', 'self')

    @staticmethod
    def prog_qsd_url(prog, name):
        """Return the url for a program-qsd with given name

        Will have .html at the end iff name does"""
        parts = name.split(":")
        if len(parts)>1:
            return "/".join([parts[0], prog.url, ":".join(parts[1:])])
        else:
            return "/".join(["programs", prog.url, name])

    @staticmethod
    def program_from_url(url):
        """ If the QSD pertains to a program, figure out which one,
            and return a tuple of the Program object and the QSD name.
            Otherwise return None.  """
        from esp.program.models import Program

        url_parts = url.split('/')
        #   The first part url_parts[0] could be anything, since prog_qsd_url()
        #   takes whatever was specified in the old qsd name
        #   (e.g. 'learn:extrasteps' results in a URL starting with 'learn/',
        #   but you could also have 'foo:extrasteps' etc.)
        #   So, allow any QSD with a program URL in the right place to match.
        if len(url_parts) > 3 and len(url_parts[3]) > 0:
            prog_url = '/'.join(url_parts[1:3])
            progs = Program.objects.filter(url=prog_url)
            if progs.count() == 1:
                if url_parts[0] == 'programs':
                    return (progs[0], '/'.join(url_parts[3:]))
                else:
                    return (progs[0], '%s:' % url_parts[0] + '/'.join(url_parts[3:]))

        return None

    def get_absolute_url(self):
        return "/"+self.url+".html"

    class Meta:
        verbose_name = 'Editable'
