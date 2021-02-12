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
from django.db.models.query import Q
from django.http import HttpResponseBadRequest, HttpResponse, HttpResponseRedirect
from django.template.loader import render_to_string

from esp.program.modules.base import ProgramModuleObj, main_call, aux_call, needs_admin
from esp.utils.web import render_to_response

from esp.program.models import ClassFlag, ClassFlagType
from esp.program.forms import ClassFlagForm
from esp.users.models import ESPUser

import json

class ClassFlagModule(ProgramModuleObj):
    doc = """Flag classes, such as for further review."""

    @classmethod
    def module_properties(cls):
        return {
            "admin_title": "Class Flags",
            "link_title": "Manage Class Flags",
            "module_type": "manage",
            "seq": 100,
            "choosable": 1,
        }

    class Meta:
        proxy = True
        app_label = 'modules'

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
            descs['flag_%s' % flag_type.id] = """Teachers who have a class with the "%s" flag""" % flag_type.name
        return descs

    @main_call
    @needs_admin
    def classflags(self, request, tl, one, two, module, extra, prog):
        """Deprecated, use the ClassSearchModule instead."""
        return HttpResponseRedirect('classsearch')

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
            response = json.dumps({
                'flag_name': render_to_string(self.baseDir()+'flag_name.html', context = context, request = request),
                'flag_detail': render_to_string(self.baseDir()+'flag_detail.html', context = context, request = request),
            })
            return HttpResponse(response, content_type='application/json')
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
