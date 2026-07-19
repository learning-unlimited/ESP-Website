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
from django.utils.timezone import now

from esp.program.modules.base import ProgramModuleObj, main_call, aux_call, needs_admin

from esp.program.models import ClassFlag, ClassFlagType
from esp.program.forms import ClassFlagForm
from esp.users.models import ESPUser

import json
import logging

logger = logging.getLogger(__name__)

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

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'

    def teachers(self, QObject = False):
        fts = ClassFlagType.get_flag_types(self.program)
        t = {}
        for flag_type in fts:
            q = Q(classsubject__flags__flag_type=flag_type.id,
                  classsubject__flags__resolved=False,
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

    def _flag_json_response(self, request, flag, include_header=False, extra=None):
        '''Render a flag as a JSON response payload.

        include_header=True adds flag_name (used when the header text may have changed,
        e.g. after a resolve/unresolve that toggles the "(Resolved)" suffix).
        '''
        context = {'flag': flag}
        payload = {
            'flag_detail': render_to_string(
                self.baseDir() + 'flag_detail.html', context=context, request=request),
        }
        if include_header:
            payload['flag_name'] = render_to_string(
                self.baseDir() + 'flag_name.html', context=context, request=request)
        if extra:
            payload.update(extra)
        return HttpResponse(json.dumps(payload), content_type='application/json')

    @aux_call
    @needs_admin
    def editflag(self, request, tl, one, two, module, extra, prog):
        '''Given a post request, take extra as the id of the flag, update its comment using the post data, and return its new detail display.'''
        if not extra or request.method != 'POST' or 'comment' not in request.POST:
            return HttpResponseBadRequest('')
        flag = ClassFlag.objects.filter(id=extra, subject__parent_program=prog).first()
        if flag is None:
            return HttpResponseBadRequest('')
        flag.comment = request.POST['comment']
        flag.save(update_fields=['comment', 'modified_by', 'modified_time'])
        return self._flag_json_response(request, flag)

    @aux_call
    @needs_admin
    def newflag(self, request, tl, one, two, module, extra, prog):
        '''Create a flag from the POST data, and return its detail display.'''
        if request.method != 'POST':
            return HttpResponseBadRequest('')
        form = ClassFlagForm(request.POST)
        if form.is_valid():
            # IDOR protection: ensure subject belongs to this program
            if form.cleaned_data['subject'].parent_program != prog:
                return HttpResponseBadRequest('')
            # IDOR protection: ensure flag_type is associated with this program
            if not prog.flag_types.filter(pk=form.cleaned_data['flag_type'].pk).exists():
                return HttpResponseBadRequest('')
            flag = form.save()
            extra_payload = None
            if flag.flag_type.notify_teacher_by_email:
                try:
                    flag.send_teacher_notification()
                except Exception:
                    logger.error("Failed to send teacher notification for flag %s on class %s",
                                 flag.id, flag.subject_id, exc_info=True)
                    extra_payload = {
                        'warning': "Flag saved, but the teacher email notification failed. "
                                   "Please notify the teacher manually."
                    }
            return self._flag_json_response(request, flag, include_header=True, extra=extra_payload)
        else:
            # The user shouldn't be able to get here unless they're doing something really weird, so let's not bother to try to tell them where the error was; since this is asynchronous that would be a bit tricky.
            return HttpResponseBadRequest('')

    @aux_call
    @needs_admin
    def deleteflag(self, request, tl, one, two, module, extra, prog):
        '''Given a post request with the ID, delete the flag.'''
        if request.method != 'POST' or 'id' not in request.POST:
            return HttpResponseBadRequest('')
        flag = ClassFlag.objects.filter(id=request.POST['id'], subject__parent_program=prog).first()
        if flag is None:
            return HttpResponseBadRequest('')
        flag.delete()
        return HttpResponse('')

    RESOLVE_UPDATE_FIELDS = ['resolved', 'resolved_by', 'resolved_time',
                             'modified_by', 'modified_time']

    @aux_call
    @needs_admin
    def resolveflag(self, request, tl, one, two, module, extra, prog):
        '''Set the resolved status of a flag. Extra is the flag ID.
        POST parameter 'action' must be 'resolve' or 'unresolve' for idempotent behavior.'''
        if not extra or request.method != 'POST':
            return HttpResponseBadRequest('')
        action = request.POST.get('action', '')
        if action not in ('resolve', 'unresolve'):
            return HttpResponseBadRequest('')
        flag = ClassFlag.objects.filter(id=extra, subject__parent_program=prog).first()
        if flag is None:
            return HttpResponseBadRequest('')
        want_resolved = (action == 'resolve')
        if want_resolved and not flag.resolved:
            flag.resolved = True
            flag.resolved_by = request.user
            flag.resolved_time = now()
            flag.save(update_fields=self.RESOLVE_UPDATE_FIELDS)
        elif not want_resolved and flag.resolved:
            flag.resolved = False
            flag.resolved_by = None
            flag.resolved_time = None
            flag.save(update_fields=self.RESOLVE_UPDATE_FIELDS)
        # If already in desired state, no-op (idempotent)
        return self._flag_json_response(request, flag, include_header=True)
