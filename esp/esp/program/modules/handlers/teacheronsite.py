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
from esp.program.modules.base import ProgramModuleObj, needs_teacher, meets_deadline, CoreModule, main_call, aux_call
from esp.program.models  import ClassSection
from esp.resources.models import Resource
from esp.utils.web import render_to_response
from esp.users.models    import Record
from esp.survey.views   import survey_view, survey_review
from esp.tagdict.models  import Tag
from datetime import datetime
from esp.program.modules.handlers.teacherclassregmodule import TeacherClassRegModule
from django.db.models import Count

class TeacherOnsite(ProgramModuleObj, CoreModule):
    @classmethod
    def module_properties(cls):
        return {
            "link_title": "Teacher Onsite",
            "admin_title": "Teacher Onsite Webapp",
            "module_type": "teach",
            "seq": 9999,
            "choosable": 1
            }

    @main_call
    @needs_teacher
    @meets_deadline('/Webapp')
    def teacheronsite(self, request, tl, one, two, module, extra, prog):
        """ Display the landing page for the teacher onsite webapp """
        user = request.user
        now = datetime.now()

        context = self.onsitecontext(request, tl, one, two, prog)

        classes = [cls for cls in user.getTaughtSections(program = prog)
                   if cls.meeting_times.all().exists()
                   and cls.resourceassignment_set.all().exists()
                   and cls.status > 0]
        # now we sort them by time/title
        classes.sort()

        context['checkin_note'] = Tag.getProgramTag('teacher_onsite_checkin_note', program = prog)
        context['webapp_page'] = 'schedule'
        context['crmi'] = prog.classregmoduleinfo
        context['classes'] = classes
        context['checked_in'] = Record.objects.filter(program=prog, event='teacher_checked_in', user=user, time__year=now.year, time__month=now.month, time__day=now.day).exists()

        return render_to_response(self.baseDir()+'schedule.html', request, context)

    @aux_call
    @needs_teacher
    @meets_deadline('/Webapp')
    def onsitemap(self, request, tl, one, two, module, extra, prog):
        context = self.onsitecontext(request, tl, one, two, prog)
        context['webapp_page'] = 'map'
        context['center'] = Tag.getProgramTag('program_center', program = prog)
        context['API_key'] = Tag.getTag('google_cloud_api_key')

        #extra should be a classroom id
        if extra:
            #gets lat/long of classroom and adds it to context
            try:
                classroom = Resource.objects.get(id=extra)
            except:
                res = None
            else:
                try:
                    res = classroom.associated_resources().get(res_type__name='Lat/Long')
                except:
                    res = None
            if res and res.attribute_value:
                classroom = res.attribute_value.split(",")
                context['classroom'] = '{lat: ' + classroom[0].strip() + ', lng: ' + classroom[1].strip() + '}'
        return render_to_response(self.baseDir()+'map.html', request, context)

    @aux_call
    @needs_teacher
    @meets_deadline('/Webapp')
    def onsitedetails(self, request, tl, one, two, module, extra, prog):
        context = self.onsitecontext(request, tl, one, two, prog)
        user = request.user
        context['webapp_page'] = 'details'
        context['section_page'] = 'info'
        secid = 0
        if extra:
            secid = extra
            sections = ClassSection.objects.filter(id = secid)
            if len(sections) != 1 or not request.user.canEdit(sections[0].parent_class):
                return render_to_response('program/modules/teacherclassregmodule/cannoteditclass.html', request, {})
        else:
            sections = user.getTaughtSections(program = prog).annotate(
                num_meeting_times=Count("meeting_times")).filter(
                num_meeting_times__gt=0, status__gt=0)
        context['sections'] = sections

        return render_to_response(self.baseDir()+'sectioninfo.html', request, context)

    @aux_call
    @needs_teacher
    @meets_deadline('/Webapp')
    def onsiteroster(self, request, tl, one, two, module, extra, prog):
        context = self.onsitecontext(request, tl, one, two, prog)
        user = request.user
        context['webapp_page'] = 'details'
        context['section_page'] = 'roster'
        context['not_found'] = []
        secid = 0
        if extra:
            secid = extra
            sections = ClassSection.objects.filter(id = secid)
            if len(sections) != 1 or not request.user.canEdit(sections[0].parent_class):
                return render_to_response('program/modules/teacherclassregmodule/cannoteditclass.html', request, {})
        else:
            sections = user.getTaughtSections(program = prog).annotate(
                num_meeting_times=Count("meeting_times")).filter(
                num_meeting_times__gt=0, status__gt=0)
        section_list = []
        for section in sections:
            sec, not_found = TeacherClassRegModule.process_attendance(section, request, prog)
            section_list.append(sec)
            context['not_found'].extend(not_found)
        context['sections'] = section_list

        return render_to_response(self.baseDir()+'sectionroster.html', request, context)

    @aux_call
    @needs_teacher
    @meets_deadline('/Webapp')
    def onsitesurvey(self, request, tl, one, two, module, extra, prog):
        context = self.onsitecontext(request, tl, one, two, prog)
        context['webapp_page'] = 'survey'
        surveys = prog.getSurveys().filter(category = tl).select_related()
        if extra == 'review':
            context['survey_page'] = 'review'
            if len(surveys):
                return survey_review(request, tl, one, two, self.baseDir()+'survey.html', context)
            else:
                return render_to_response(self.baseDir()+'survey.html', request, context)
        else:
            context['survey_page'] = 'survey'
            return survey_view(request, tl, one, two, self.baseDir()+'survey.html', context)

    @staticmethod
    def onsitecontext(request, tl, one, two, prog):
        context = {}
        surveys = prog.getSurveys().filter(category = tl).select_related()
        if len(surveys) == 0:
            context['survey_status'] = 'none'
        context['user'] = request.user
        context['program'] = prog
        context['one'] = one
        context['two'] = two
        return context

    def isStep(self):
        return Tag.getBooleanTag('teacher_webapp_isstep', program=self.program)

    class Meta:
        proxy = True
        app_label = 'modules'
