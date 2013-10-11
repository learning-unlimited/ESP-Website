
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

import datetime
import json

from esp.program.modules.base    import ProgramModuleObj, main_call, aux_call, meets_deadline, needs_student, meets_grade
from esp.program.models          import ClassSubject, RegistrationType, StudentSubjectInterest
from esp.users.models            import User, ESPUser, UserAvailability
from esp.web.util                import render_to_response
from django.core.exceptions      import ObjectDoesNotExist
from django.http                 import HttpResponse, HttpResponseBadRequest
from django.db.models.query      import Q
    
class StudentRegPhase1(ProgramModuleObj):

    def students(self, QObject = False):
        # TODO: fill this in
        q = Q()
        if QObject:
            return {'phase1_students': q}
        else:
            return {'phase1_students': ESPUser.objects.filter(q).distinct()}

    def studentDesc(self):
        return {'phase1_students': "Students who have completed student registration phase 1"}

    def isCompleted(self):
        # TODO: fill this in
        return True

    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Student Registration Phase 1",
            "admin_title": "Student Registration Phase 1",
            "module_type": "learn",
            "seq": 5
            }
    
    @main_call
    @needs_student
    @meets_grade
    @meets_deadline('/Classes/Lottery')
    def studentreg_1(self, request, tl, one, two, module, extra, prog):
        return render_to_response(self.baseDir() + 'studentreg_1.html', request, {})

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Classes/Lottery')
    def mark_classes_interested(self, request, tl, one, two, module, extra, prog):
        """
        Saves the set of classes marked as interested by the student.

        Ex: request.POST['json_data'] = {
            'interested': [1,5,3,9],
            'not_interested': [4,6,10]
        }
        """
        if not 'json_data' in request.POST:
            return HttpResponseBadRequest('JSON data not included in request.')
        json_data = json.loads(request.POST['json_data'])
        if not 'interested' in json_data or not 'not_interested' in json_data:
            return HttpResponseBadRequest('JSON data mis-formatted.')
        try:
            interested_type, created = RegistrationType.objects.get_or_create(
                name='Interested', category='student')
            # Unexpire any matching SSIs that exist already (to avoid creating
            # duplicate objects).
            ssi_qs = StudentSubjectInterest.objects.filter(
                user=request.user, subject__pk__in=json_data['interested'],
                subject__parent_program=prog, subject__status__gte=0)
            ssi_qs.update(end_date=None)
            # Determine which ids are valid and haven't been created yet and
            # bulk create those objects.
            existing_ids = ssi_qs.values_list('subject__id', flat=True)
            valid_ids = ClassSubject.objects.filter(
                pk__in=json_data['interested'], parent_program=prog,
                status__gte=0).values_list('id', flat=True)
            to_create_ids = set(valid_ids)-set(existing_ids)
            StudentSubjectInterest.objects.bulk_create([
                    StudentSubjectInterest(
                        user=request.user,
                        subject=ClassSubject.objects.get(id=subj_id))
                    for subj_id in to_create_ids])
            # Expire any matching SSIs that are in 'not_interested'
            StudentSubjectInterest.objects.filter(
                user=request.user, subject__pk__in=json_data['not_interested']
                ).update(end_date=datetime.datetime.now())
        # Catch a misformatted JSON string
        except TypeError:
            return HttpResponseBadRequest('JSON data mis-formatted.')

        return HttpResponse()

    @aux_call
    @needs_student
    @meets_grade
    @meets_deadline('/Classes/Lottery')
    def mark_class_interested(self, request, tl, one, two, module, extra, prog):
        """
        Saves the single class indicated as interested or not.

        Ex: request.POST['json_data'] = {
            'id': 1234,
            'interested': true
        }
        """
        if not 'json_data' in request.POST:
            return HttpResponseBadRequest('JSON data not included in request.')
        json_data = json.loads(request.POST['json_data'])
        if not 'id' in json_data and not 'interested' in json_data:
            return HttpResponseBadRequest('JSON data missing keys.')
        id = json_data['id']
        interested = json_data['interested']
        if type(id) != int or type(interested) != bool:
            return HttpResponseBadRequest('JSON data value types incorrect.')
        if ClassSubject.objects.filter(
            pk=id, parent_program=prog, status__gte=0).count() == 0:
            return HttpResponseBadRequest('Class subject specified is invalid.')
        interested_type, created = RegistrationType.objects.get_or_create(
            name='Interested', category='student')

        if interested:
            # If the SSI exists, unexpire it, otherwise create it.
            obj, created = StudentSubjectInterest.objects.get_or_create(
                subject=ClassSubject.objects.get(id=id), user=request.user)
            if not created:
                obj.unexpire()
        else:
            qs = StudentSubjectInterest.objects.filter(
                subject=id, user=request.user)
            # If the SSI exists, and there's only one, expire it.
            if len(qs) > 1:
                return HttpResponseBadRequest(
                    'Multiple student registrations match update.')
            elif len(qs) == 1:
                qs[0].expire()

        return HttpResponse()

    
    class Meta:
        abstract = True
