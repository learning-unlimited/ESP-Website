import json

from django.http import HttpResponse

from esp.middleware import ESPError
from esp.program.models import ClassSection
from esp.program.modules.admin_search import AdminSearchEntry
from esp.program.modules.base import ProgramModuleObj, main_call, aux_call, needs_onsite
from esp.utils.web import render_to_response


class AdminOnsiteWebapp(ProgramModuleObj):
    """Mobile-friendly onsite admin dashboard with live class status."""

    @classmethod
    def module_properties(cls):
        return {
            'admin_title': 'Admin Onsite Webapp',
            'link_title': 'Admin Onsite Webapp',
            'module_type': 'onsite',
            'seq': 6,
            'choosable': 1,
        }

    @classmethod
    def get_admin_search_entry(cls, program, tl, view_name, pmo):
        if tl != 'onsite' or view_name != 'onsite_admin':
            return None
        return AdminSearchEntry(
            id='onsite_admin_webapp',
            url='/onsite/%s/onsite_admin' % program.getUrlBase(),
            title='Onsite Admin Webapp',
            category='Quick Links',
            keywords=['onsite', 'admin', 'checkin', 'registration', 'class'],
        )

    def _assert_program_admin(self, request):
        if not request.user.isAdmin(self.program):
            raise ESPError('You need program admin permissions to use this page.', log=False)

    @staticmethod
    def _serialize_section(section):
        enrolled = int(section.enrolled_students or 0)
        checkins = int(section.attending_students or 0)
        capacity = int(section.capacity or 0)
        teachers_obj = section.teachers.all() if hasattr(section.teachers, 'all') else section.teachers
        return {
            'section_id': section.id,
            'emailcode': section.emailcode(),
            'title': section.title(),
            'teachers': ', '.join([teacher.name() for teacher in teachers_obj]),
            'rooms': section.prettyrooms(),
            'registration_open': section.isRegOpen(),
            'enrolled': enrolled,
            'checkins': checkins,
            'capacity': capacity,
        }

    def _sections(self):
        return ClassSection.objects.filter(
            parent_class__parent_program=self.program,
            parent_class__status__gt=0,
            status__gt=0,
        ).select_related('parent_class').prefetch_related('teachers', 'meeting_times')

    @main_call
    @needs_onsite
    def onsite_admin(self, request, tl, one, two, module, extra, prog):
        self._assert_program_admin(request)
        context = {
            'program': prog,
            'one': one,
            'two': two,
            'refresh_seconds': 12,
        }
        return render_to_response(self.baseDir() + 'dashboard.html', request, context)

    @aux_call
    @needs_onsite
    def onsite_admin_data(self, request, tl, one, two, module, extra, prog):
        self._assert_program_admin(request)
        sections = [self._serialize_section(sec) for sec in self._sections()]
        payload = {
            'refresh_seconds': 12,
            'stats': {
                'total_classes': len(sections),
                'enrolled_total': sum(section['enrolled'] for section in sections),
                'checkins_total': sum(section['checkins'] for section in sections),
            },
            'classes': sections,
        }
        resp = HttpResponse(content_type='application/json')
        json.dump(payload, resp)
        return resp

    def isStep(self):
        return False

    class Meta:
        proxy = True
        app_label = 'modules'