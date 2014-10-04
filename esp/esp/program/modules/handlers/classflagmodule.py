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

import datetime
import json
import operator

from esp.program.modules.base import ProgramModuleObj, main_call, aux_call, needs_admin
from esp.cache           import cache_function
from esp.web.util        import render_to_response
from esp.utils.query_utils import nest_Q

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
            q = Q(classsubject__flags__flag_type=flag_type.id,
                  classsubject__parent_program=self.program)
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
        '''Takes a dict from classflags and returns a QuerySet.

        The dict is decoded from the json sent by the javascript in
        /manage///classflags/; the format is specified in the docstring of
        classflags() below.
        '''
        base = ClassSubject.objects.filter(parent_program=self.program)
        time_fmt = "%m/%d/%Y %H:%M"
        query_type = j['type']
        value = j.get('value')
        if 'flag' in query_type:
            lookups = {}
            if 'id' in value:
                lookups['flag_type'] = value['id']
            for time_type in ['created', 'modified']:
                when = value.get(time_type + '_when')
                lookup = time_type + '_time'
                if when == 'before':
                    lookup += '__lt'
                elif when == 'after':
                    lookup += '__gt'
                if when:
                    lookups[lookup] = datetime.datetime.strptime(value[time_type+'_time'], time_fmt)
            if 'not' in query_type:
                # Due to https://code.djangoproject.com/ticket/14645, we have
                # to write this query a little weirdly.
                return base.exclude(id__in=ClassFlag.objects.filter(**lookups).values('subject'))
            else:
                return base.filter(nest_Q(Q(**lookups), 'flags'))
        elif query_type == 'category':
            return base.filter(category=value)
        elif query_type == 'not category':
            return base.exclude(category=value)
        elif query_type == 'status':
            return base.filter(status=value)
        elif query_type == 'not status':
            return base.exclude(status=value)
        elif 'scheduled' in query_type:
            lookup = 'sections__meeting_times__isnull'
            if 'some sections' in query_type:
                # Get classes with sections with meeting times.
                return base.filter(**{lookup: False})
            elif 'not all sections' in query_type:
                # Get classes with sections with meeting times.
                return base.filter(**{lookup: True})
            elif 'all sections' in query_type:
                # Exclude classes with sections with no meeting times.
                return base.exclude(**{lookup: True})
            elif 'no sections' in query_type:
                # Exclude classes with sections with meeting times.
                return base.exclude(**{lookup: False})
        else:
            # Here v is going to be a list of subqueries.  First, evaluate them.
            subqueries = [self.jsonToQuerySet(query_json) for query_json in value]
            if query_type == 'all':
                return reduce(operator.and_, subqueries)
            elif query_type == 'any':
                return reduce(operator.or_, subqueries)
            elif query_type == 'none':
                return base.exclude(pk__in=reduce(operator.or_, subqueries))
            elif query_type == 'not all':
                return base.exclude(pk__in=reduce(operator.and_, subqueries))
            else:
                raise ESPError('Invalid json for flag query builder!')

    def jsonToEnglish(self, j):
        '''Takes a dict from classflags and returns something human-readable.

        The dict is decoded from the json sent by the javascript in
        /manage///classflags/; the format is specified in the docstring of
        classflags() below.
        '''
        query_type = j['type']
        value = j.get('value')
        if 'flag' in query_type:
            if 'id' in value:
                base = (query_type[:-4] + 'the flag "' +
                        ClassFlagType.objects.get(id=value['id']).name + '"')
            elif 'not' in query_type:
                base = 'not flags'
            else:
                base = 'any flag'
            modifiers = []
            for time_type in ['created', 'modified']:
                if time_type+'_when' in value:
                    modifiers.append(time_type + " " +
                                     value[time_type + '_when'] + " " +
                                     value[time_type + '_time'])
            base += ' '+' and '.join(modifiers)
            return base
        elif 'category' in query_type:
            return (query_type[:-8] + 'the category "' +
                    str(ClassCategories.objects.get(id=value)) + '"')
        elif 'status' in query_type:
            statusname = {
                10: 'Accepted',
                5: 'Accepted but hidden',
                0: 'Unreviewed',
                -10: 'Rejected',
                -20: 'Cancelled',
                }[int(value)]
            return query_type[:-6]+'the status "'+statusname+'"'
        elif 'scheduled' in query_type:
            return query_type
        else:
            subqueries = [self.jsonToEnglish(query) for query in value]
            return query_type+" of ("+', '.join(subqueries)+")"

    @main_call
    @needs_admin
    def classflags(self, request, tl, one, two, module, extra, prog):
        '''An interface to query for some boolean expression of flags.

        The front-end javascript will allow the user to build a query, then
        POST it in the form of a json.  The response to said post should be the
        list of classes matching the flag query.

        The json should be a single object, with keys 'type' and 'value'.  The
        type of 'value' depends on the value of 'type':
            * If 'type' is 'flag' or 'not flag', 'value' should be an object,
            with some or all of the keys 'id', 'created_time', 'modified_time'
            (all should be strings).
            * If 'type' is 'category', 'not category', 'status', or
            'not status', 'value' should be a string.
            * If 'type' is 'some sections schedule',
            'not all sections scheduled', 'all sections scheduled', or
            'no sections scheduled', 'value' should be omitted.
            * If 'type' is 'all', 'any', 'none', or 'not all', 'value' should
            be an array of objects of the same form.
        '''
        # Grab the data from either a GET or a POST.
        # We allow a GET request to make them linkable, and POST requests for
        # some kind of backwards-compatibility with the way the interface
        # previously worked.
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
             # The prefetch lets us do basically all of the processing on the template level.
            queryset = self.jsonToQuerySet(decoded).distinct().order_by('id').prefetch_related(
                'flags', 'flags__flag_type', 'teachers', 'category', 'sections')
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
