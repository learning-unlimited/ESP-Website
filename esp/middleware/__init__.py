import re
from operator import add
from time import time
from django.db import connection

class StatsMiddleware(object):

    def process_view(self, request, view_func, view_args, view_kwargs):


        from django.conf import settings
        debug = settings.DEBUG

        if debug:
            # get number of db queries before we do anything
            n = len(connection.queries)

        # time the view
        start = time()
        response = view_func(request, *view_args, **view_kwargs)
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

        if settings.DISPLAYSQL and settings.DEBUG:
            sqlcontent = "\n\n"+'<div class="sql">'
            for q in connection.queries:
                sqlcontent += "\n"+'%s:&nbsp;&nbsp;%s<br />' % \
                              (q['time'], q['sql'])
            sqlcontent += "\n\n</div>"

            pos = response.content.find('</body>')
            response.content = response.content[:pos] + \
                               sqlcontent + \
                               response.content[pos:]

        return response
