
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
import re
from operator import add
from time import time
from django.db import connection
from django.views.decorators.vary import vary_on_headers

try:
    import cPickle as pickle
except ImportError:
    import pickle

import base64

class StatsMiddleware(object):
    """ Inspiration from http://davidavraamides.net/blog/2006/07/03/page-stats-middleware/"""
    @staticmethod
    def process_view(request, view_func, view_args, view_kwargs):


        from django.conf import settings
        debug = settings.DEBUG

        if debug:
            # get number of db queries before we do anything
            n = len(connection.queries)

        # time the view
        start = time()
        try:
            view_func = vary_on_headers('Cookie')(view_func)
            response = view_func(request, *view_args, **view_kwargs)
        except Exception, e:
            from esp.middleware import ESPErrorMiddleware
            response = ESPErrorMiddleware().process_exception(request, e)
            if response:
                return response
            raise e
            
        totTime = time() - start

        stats = {
            'totTime': totTime,
            'dbInfo': ''
            }

        if debug:
            # compute the db time for the queries just run
            queries = len(connection.queries) - n
            if queries:
                dbTime = reduce(add, [float(q['time']) 
                                      for q in connection.queries[n:]])
            else:
                dbTime = 0.0

            # and backout python time
            pyTime = totTime - dbTime

            stats['dbInfo'] = ' Code: %(pyTime).2fs DB: %(dbTime).2fs Queries: %(queries).d' \
                              %  {'pyTime': pyTime,
                                  'dbTime': dbTime,
                                  'queries':queries}

        

        # replace the comment if found            
        if response and response.content:
            s = response.content
            regexp = re.compile(r'(?P<cmt><!--\s*STATS:(?P<fmt>.*?)-->)')
            match = regexp.search(s)
            if match:
                s = s[:match.start('cmt')] + \
                    match.group('fmt') % stats + \
                    s[match.end('cmt'):]
                response.content = s

        if settings.DISPLAYSQL and settings.DEBUG and \
           request.META['REMOTE_ADDR'] in settings.INTERNAL_IPS:
            sqlcontent = "\n\n"+'<div class="sql">\n'
            #sqlcontent += base64.encodestring(pickle.dumps(connection.queries))
            
            for q in connection.queries:
                sqlcontent += "\n"+'%s:&nbsp;&nbsp;%s<br />' % \
                              (q['time'], q['sql'])
            sqlcontent += "\n\n</div>"

            if '</body>' in response.content.lower():
                pos = response.content.find('</body>')
                response.content = response.content[:pos] + \
                                   sqlcontent + \
                                   response.content[pos:]

        return response

