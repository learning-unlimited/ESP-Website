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
from django.db.models.query import Q
from django.http import HttpResponseBadRequest, HttpResponse

import json
import operator

from esp.program.modules.base import ProgramModuleObj, main_call, aux_call, needs_admin
from esp.cache           import cache_function
from esp.web.util        import render_to_response

from esp.program.models import ClassSubject, ClassFlag, ClassFlagType, ClassCategories
from esp.program.forms import ClassFlagForm
from esp.users.models import ESPUser


class ClassFlagModule(ProgramModuleObj):
    doc = """ Flag classes, such as for further review.  Find all classes matching certain flags, and so on. """
    @classmethod
    def module_properties(cls):
        return {
                "admin_title": "Class Flags",
                "link_title": "Manage Class Flags",
                "module_type": "manage",
                "seq": 100,
                }

    class Meta:
        proxy = True
    
    def teachers(self, QObject = False):
        fts = ClassFlagType.get_flag_types(self.program)
        t = {}
        for flag_type in fts:
            q = Q(classsubject__flags__flag_type=flag_type.id)
            if QObject:
                t['flag_%s' % flag_type.id] = q
            else:
                t['flag_%s' % flag_type.id] = ESPUser.objects.filter(q).distinct()
        return t
    
    def teacherDesc(self):
        fts = ClassFlagType.get_flag_types(self.program)
        descs = {}
        for flag_type in fts:
            descs['flag_%s' % flag_type.id] = """Teachers who have a class with the "%s" flag.""" % flag_type.name
        return descs

    def jsonToQuerySet(self, j):
        '''Takes a dict decoded from the json sent by the javascript in /manage///classflags/ and converts it to QuerySet.'''
        base = ClassSubject.objects.filter(parent_program=self.program)
        lookup = 'flags__flag_type'
        t = j['type']
        v = j['value']
        if t=='flag':
            return base.filter(**{lookup: v})
        elif t=='not flag':
            return base.exclude(**{lookup: v})
        elif t=='category':
            return base.filter(category=v)
        elif t=='not category':
            return base.exclude(category=v)
        elif t=='status':
            return base.filter(status=v)
        elif t=='not status':
            return base.exclude(status=v)
        else:
            # Here v is going to be a list of subqueries.  First, evaluate them.
            subqueries = [self.jsonToQuerySet(i) for i in v]
            if t=='all':
                return reduce(operator.and_, subqueries)
            elif t=='any':
                return reduce(operator.or_, subqueries)
            elif t=='none':
                return base.exclude(pk__in=reduce(operator.or_, subqueries))
            elif t=='not all':
                return base.exclude(pk__in=reduce(operator.and_, subqueries))
            else:
                raise ESPError('Invalid json for flag query builder!')

    def jsonToEnglish(self, j):
        '''Takes a dict decided from the json sent by the javscript in /manage///classflags/ and converts it to something vaguely human-readable.'''
        t = j['type']
        v = j['value']
        if 'flag' in t:
            return t[:-4]+'the flag "'+ClassFlagType.objects.get(id=v).name+'"'
        if 'category' in t:
            return t[:-8]+'the category "'+str(ClassCategories.objects.get(id=v))+'"'
        if 'status' in t:
            statusname = {
                    10: 'Accepted',
                    5: 'Accepted but hidden',
                    0: 'Unreviewed',
                    -10: 'Rejected',
                    -20: 'Cancelled',
                    }[int(v)]
            return t[:-6]+'the status "'+statusname+'"'
        else:
            subqueries = [self.jsonToEnglish(i) for i in v]
            return t+" of ("+', '.join(subqueries)+")"

    @main_call
    @needs_admin
    def classflags(self, request, tl, one, two, module, extra, prog):
        '''An interface to query for some boolean expression of flags.  The front-end javascript will allow the user to build a query, then POST it in the form of a json.  The response to said post should be the list of classes matching the flag query.

        The json should be a single object, which should have two keys: "type" and "value".  The value of the "type" key should be a string, one of the set ["flag", "not flag", "all", "any", "not all", "none"].  In the first two cases, the value of the "value" key should be the id of a flag.  In the latter four cases, it should be a list of objects of the same form.'''
        # Grab the data from either a GET or a POST.
        # We allow a GET request to make them linkable, and POST requests for some kind of backwards-compatibility with the way the interface previously worked.
        if request.method == 'GET':
            if 'query' in request.GET:
                data = request.GET['query']
            else:
                data = None
        else:
            data = request.POST['query']
        context = {
                'flag_types': ClassFlagType.get_flag_types(self.program),
                'prog': self.program,
                }
        if data is None:
            # We should display the query builder interface.
            fts = ClassFlagType.get_flag_types(self.program)
            context['categories'] = self.program.class_categories.all()
            return render_to_response(self.baseDir()+'flag_query_builder.html', request, context)
        else:
            # They've sent a query, let's process it.
            decoded = json.loads(data)
            queryset = self.jsonToQuerySet(decoded).distinct().order_by('id').prefetch_related('flags', 'flags__flag_type', 'teachers') # The prefetch lets us do basically all of the processing on the template level.
            english = self.jsonToEnglish(decoded)
            context['queryset']=queryset
            context['english']=english
            return render_to_response(self.baseDir()+'flag_results.html', request, context)


    @aux_call
    @needs_admin
    def editflag(self, request, tl, one, two, module, extra, prog):
        '''Given a post request, take extra as the id of the flag, update its comment using the post data, and return its new detail display.'''
        if not extra or request.method != 'POST' or 'comment' not in request.POST:
            return HttpResponseBadRequest('')
        results = ClassFlag.objects.filter(id=extra)
        if not len(results): #Use len() since we will evaluate it anyway
            return HttpResponseBadRequest('')
        flag = results[0]
        flag.comment = request.POST['comment']
        flag.save()
        context = { 'flag' : flag }
        return render_to_response(self.baseDir()+'flag_detail.html', request, context)

    @aux_call
    @needs_admin
    def newflag(self, request, tl, one, two, module, extra, prog):
        '''Create a flag from the POST data, and return its detail display.'''
        if request.method != 'POST':
            return HttpResponseBadRequest('')
        form = ClassFlagForm(request.POST)
        if form.is_valid():
            flag = form.save()
            context = { 'flag' : flag }
            return render_to_response(self.baseDir()+'flag_detail.html', request, context)
        else:
            # The user shouldn't be able to get here unless they're doing something really weird, so let's not bother to try to tell them where the error was; since this is asynchronous that would be a bit tricky.
            return HttpResponseBadRequest('')

    @aux_call
    @needs_admin
    def deleteflag(self, request, tl, one, two, module, extra, prog):
        '''Given a post request with the ID, delete the flag.'''
        if request.method != 'POST' or 'id' not in request.POST:
            return HttpResponseBadRequest('')
        results = ClassFlag.objects.filter(id=request.POST['id'])
        if not len(results): #Use len() since we will evaluate it anyway
            return HttpResponseBadRequest('')
        flag = results[0]
        flag.delete()
        return HttpResponse('')
