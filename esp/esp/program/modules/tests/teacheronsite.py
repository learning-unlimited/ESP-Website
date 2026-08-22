"""
Unit tests for TeacherOnsite (teacheronsite.py).
"""
from esp.program.modules.handlers.teacheronsite import TeacherOnsite
from esp.program.modules.tests.support import ModuleHandlerTestMixin
from esp.program.tests import ProgramFrameworkTest
from esp.survey.models import Survey
from esp.users.models import RecordType


class TeacherOnsiteTest(ModuleHandlerTestMixin, ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        kwargs.update({
            'num_students': 1,
            'num_teachers': 2,
            'num_admins': 1,
            'num_timeslots': 3,
            'num_rooms': 3,
        })
        super().setUp(*args, **kwargs)
        self.add_user_profiles()
        self.schedule_randomly()
        # TeacherOnsite is a CoreModule; disable required-module gating so
        # requests reach its views instead of incomplete required modules.
        scrmi = self.program.studentclassregmoduleinfo
        scrmi.force_show_required_modules = False
        scrmi.save()
        self.module = self.get_module_obj('TeacherOnsite')
        RecordType.objects.get_or_create(
            name='teacher_checked_in',
            defaults={'description': 'Teacher checked in for teaching on the day of the program'},
        )
        # onsitesurvey delegates to survey_view, which 500s without a teach survey.
        Survey.objects.get_or_create(
            name='Teacher Onsite Test Survey',
            program=self.program,
            category='teach',
        )

    def test_teacheronsite_landing_page(self):
        self.login_as('teacher')
        response = self.assert_view_ok(self.get_module_url('teach', 'teacheronsite'))
        self.assertEqual(response.context['webapp_page'], 'schedule')
        self.assertIn('classes', response.context)
        self.assertGreaterEqual(len(response.context['classes']), 1)
        self.assertIn('checked_in', response.context)
        self.assertTemplateUsed(response, 'program/modules/teacheronsite/schedule.html')

    def test_student_cannot_access_teacheronsite(self):
        self.login_as('student')
        response = self.client.get(self.get_module_url('teach', 'teacheronsite'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'errors/program/notateacher.html')

    def test_onsitemap_page(self):
        self.login_as('teacher')
        response = self.assert_view_ok(self.get_module_url('teach', 'onsitemap'))
        self.assertEqual(response.context['webapp_page'], 'map')
        self.assertIn('center', response.context)
        self.assertIn('zoom', response.context)
        self.assertTemplateUsed(response, 'program/modules/teacheronsite/map.html')

    def test_onsitedetails_page(self):
        self.login_as('teacher')
        response = self.assert_view_ok(self.get_module_url('teach', 'onsitedetails'))
        self.assertEqual(response.context['webapp_page'], 'details')
        self.assertEqual(response.context['section_page'], 'info')
        self.assertIn('sections', response.context)
        self.assertGreaterEqual(len(response.context['sections']), 1)
        self.assertTemplateUsed(response, 'program/modules/teacheronsite/sectioninfo.html')

    def test_onsiteroster_page(self):
        self.login_as('teacher')
        response = self.assert_view_ok(self.get_module_url('teach', 'onsiteroster'))
        self.assertEqual(response.context['webapp_page'], 'details')
        self.assertEqual(response.context['section_page'], 'roster')
        self.assertIn('sections', response.context)
        self.assertGreaterEqual(len(response.context['sections']), 1)
        self.assertIn('not_found', response.context)
        self.assertTemplateUsed(response, 'program/modules/teacheronsite/sectionroster.html')

    def test_onsitesurvey_page(self):
        self.login_as('teacher')
        response = self.assert_view_ok(self.get_module_url('teach', 'onsitesurvey'))
        self.assertEqual(response.context['webapp_page'], 'survey')
        self.assertEqual(response.context['survey_page'], 'survey')

    def test_get_admin_search_entry_main_view(self):
        entry = TeacherOnsite.get_admin_search_entry(
            self.program, 'teach', 'teacheronsite', self.module
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry.title, 'Teacher Onsite')
        self.assertIn('teacher', entry.keywords)

    def test_get_admin_search_entry_unknown_view(self):
        entry = TeacherOnsite.get_admin_search_entry(
            self.program, 'teach', 'not_a_real_view', self.module
        )
        self.assertIsNone(entry)

    def test_get_admin_search_entry_roster(self):
        entry = TeacherOnsite.get_admin_search_entry(
            self.program, 'teach', 'onsiteroster', self.module
        )
        self.assertIsNotNone(entry)
        self.assertIn('roster', entry.title.lower())

    def test_onsitecontext_sets_program_and_user(self):
        self.login_as('teacher')
        response = self.client.get(self.get_module_url('teach', 'teacheronsite'))
        self.assertEqual(response.context['program'], self.program)
        self.assertEqual(response.context['user'], self.teachers[0])

    def test_onsitecontext_helper_directly(self):
        class Req:
            user = self.teachers[0]
        ctx = TeacherOnsite.onsitecontext(Req(), 'teach', 'one', 'two', self.program)
        self.assertEqual(ctx['program'], self.program)
        self.assertEqual(ctx['user'], self.teachers[0])
        self.assertIn('map_tab', ctx)
