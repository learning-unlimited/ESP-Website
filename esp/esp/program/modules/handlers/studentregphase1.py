
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

from django.http                 import HttpResponse, HttpResponseBadRequest
from django.db.models.query      import Q

from esp.program.modules.base    import ProgramModuleObj, main_call, aux_call, meets_deadline, needs_student, meets_grade
from esp.program.models          import ClassSubject, RegistrationType, StudentSubjectInterest
from esp.users.models            import User, ESPUser, UserAvailability
from esp.web.util                import render_to_response
    
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
        # get choices for filtering options
        context = {}

        def group_columns(items):
            # collect into groups of 5
            cols = []
            for i, item in enumerate(items):
                if i % 5 == 0:
                    col = []
                    cols.append(col)
                col.append(item)
            return cols

        category_choices = []
        for category in prog.class_categories.all():
            category_choices.append((category.id, category.category))
        context['category_choices'] = group_columns(category_choices)

        grade_choices = []
        grade_choices.append(('ALL', 'All'))
        for grade in range(prog.grade_min, prog.grade_max + 1):
            grade_choices.append((grade, grade))
        context['grade_choices'] = group_columns(grade_choices)

        return render_to_response(self.baseDir() + 'studentreg_1.html', request, context)

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
        try:
            json_data = json.loads(request.POST['json_data'])
        except ValueError:
            return HttpResponseBadRequest('JSON data mis-formatted.')
        if not isinstance(json_data.get('interested'), list) or \
           not isinstance(json_data.get('not_interested'), list):
            return HttpResponseBadRequest('JSON data mis-formatted.')

        # Determine which of the given class ids are valid
        valid_ids = ClassSubject.objects.filter(
            pk__in=json_data['interested'],
            parent_program=prog,
            status__gte=0).values_list('pk', flat=True)
        # Unexpire any matching SSIs that exist already (to avoid
        # creating duplicate objects).
        to_unexpire = StudentSubjectInterest.objects.filter(
            user=request.user,
            subject__pk__in=valid_ids)
        to_unexpire.update(end_date=None)
        # Determine which valid ids haven't had SSIs created yet
        # and bulk create those objects.
        existing_ids = to_unexpire.values_list('subject__pk', flat=True)
        to_create_ids = set(valid_ids) - set(existing_ids)
        StudentSubjectInterest.objects.bulk_create([
            StudentSubjectInterest(
                user=request.user,
                subject_id=subj_id)
            for subj_id in to_create_ids])
        # Expire any matching SSIs that are in 'not_interested'
        to_expire = StudentSubjectInterest.objects.filter(
            user=request.user,
            subject__pk__in=json_data['not_interested'])
        to_expire.update(end_date=datetime.datetime.now())

        return HttpResponse()

    
    class Meta:
        abstract = True
