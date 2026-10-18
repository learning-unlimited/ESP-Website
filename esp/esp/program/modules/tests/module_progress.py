__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2024 by the individual contributors
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

from unittest import mock

from django.template import Context
from django.test import RequestFactory, SimpleTestCase

from esp.program.models import ProgramModule
from esp.program.modules.base import ProgramModuleObj
from esp.program.modules.checklist import get_checklist_progress, get_module_page_checklist_context
from esp.program.templatetags.modules import registration_progress, teacher_checklist
from esp.program.tests import ProgramFrameworkTest
from esp.themes.controllers import ThemeController


class RegistrationProgressTagTest(ProgramFrameworkTest):
    """Unit tests for the registration_progress template tag.

    These tests call the tag function directly using a RequestFactory-built
    request, so no URL routing or permission setup is required.
    """

    def setUp(self):
        super().setUp()
        # Enable checkboxes (progress_mode=1) so the tag has something to render
        self.scrmi = self.program.studentclassregmoduleinfo
        self.scrmi.progress_mode = 1
        self.scrmi.save()

    def _make_request(self, tl=None, with_program=True):
        rf = RequestFactory()
        request = rf.get('/')
        request.user = self.students[0]
        if with_program:
            request.program = self.program
        if tl is not None:
            request.tl = tl
        return request

    def test_returns_empty_without_request_in_context(self):
        """Tag returns empty dict when there is no request in the template context."""
        result = registration_progress({})
        self.assertEqual(result, {})

    def test_returns_empty_without_program_on_request(self):
        """Tag returns empty dict when request has no program attribute."""
        request = self._make_request(with_program=False, tl='learn')
        result = registration_progress({'request': request})
        self.assertEqual(result, {})

    def test_returns_empty_without_tl_on_request(self):
        """Tag returns empty dict when request.tl is not set."""
        request = self._make_request()  # no tl
        result = registration_progress({'request': request})
        self.assertEqual(result, {})

    def test_returns_empty_for_manage_tl(self):
        """Tag returns empty dict for admin/manage tl (not a registration flow)."""
        request = self._make_request(tl='manage')
        result = registration_progress({'request': request})
        self.assertEqual(result, {})

    def test_returns_empty_when_progress_mode_disabled(self):
        """Tag returns empty dict when progress_mode is 0 (none)."""
        self.scrmi.progress_mode = 0
        self.scrmi.save()
        request = self._make_request(tl='learn')
        result = registration_progress({'request': request})
        self.assertEqual(result, {})

    def test_returns_context_for_learn_tl(self):
        """Tag returns the expected context keys for a student (learn) tl."""
        request = self._make_request(tl='learn')
        result = registration_progress({'request': request})
        self.assertIn('modules', result)
        self.assertIn('scrmi', result)
        self.assertIn('completedAll', result)
        self.assertIn('program', result)
        self.assertIn('extra_steps', result)
        self.assertEqual(result['extra_steps'], 'learn:extra_steps')
        self.assertEqual(result['program'], self.program)
        self.assertEqual(result['scrmi'], self.scrmi)

    def test_returns_correct_extra_steps_for_teach_tl(self):
        """Tag uses 'teach:extra_steps' for the teacher registration tl."""
        crmi = self.program.classregmoduleinfo
        crmi.progress_mode = 1
        crmi.save()
        request = self._make_request(tl='teach')
        result = registration_progress({'request': request})
        self.assertNotEqual(result, {})
        self.assertIn('extra_steps', result)
        self.assertEqual(result['extra_steps'], 'teach:extra_steps')

    def test_completedAll_false_when_required_module_incomplete(self):
        """completedAll is False when a required module has not been completed."""
        # Make StudentAcknowledgementModule required for this program
        pm = ProgramModule.objects.get(handler='StudentAcknowledgementModule')
        pmo = ProgramModuleObj.getFromProgModule(self.program, pm)
        pmo.__class__ = ProgramModuleObj
        pmo.required = True
        pmo.save()

        request = self._make_request(tl='learn')
        result = registration_progress({'request': request})

        self.assertIn('completedAll', result)
        # student0 has not submitted the acknowledgement, so completedAll should be False
        self.assertFalse(result['completedAll'])

    def test_completedAll_true_when_no_required_modules(self):
        """completedAll is True when no required modules exist for the program."""
        # Make all modules non-required
        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()

        request = self._make_request(tl='learn')
        result = registration_progress({'request': request})

        self.assertIn('completedAll', result)
        self.assertTrue(result['completedAll'])


class RequiredModuleProgressIntegrationTest(ProgramFrameworkTest):
    """Integration tests: required module pages show the progress checklist.

    These tests use the Django test client to make full HTTP requests.
    The program is set up with StudentAcknowledgementModule as the only
    required module, force_show_required_modules=True, and progress_mode=1
    (checkboxes).

    The test student has Student/All permission (set up by ProgramFrameworkTest)
    so they can reach all student-facing module pages.
    """

    # Text that appears in the checklist table header (checkboxes.html)
    CHECKLIST_MARKER = 'Steps for Registration'

    def setUp(self):
        super().setUp()
        self.add_user_profiles()

        # Make only StudentAcknowledgementModule required; silence all others
        ack_pm = ProgramModule.objects.get(handler='StudentAcknowledgementModule')
        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = (pmo.module == ack_pm)
            pmo.save()

        # Enable the required-module redirect flow with the checkboxes UI
        self.scrmi = self.program.studentclassregmoduleinfo
        self.scrmi.force_show_required_modules = True
        self.scrmi.progress_mode = 1
        self.scrmi.save()

        # Log in as the first test student
        self.student = self.students[0]
        self.client.login(username=self.student.username, password='password')

    def test_required_module_page_shows_progress_checklist(self):
        """Visiting studentreg with an incomplete required module should
        serve the required module page including the registration checklist."""
        response = self.client.get('/learn/%s/studentreg' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.CHECKLIST_MARKER)

    def test_no_checklist_when_progress_mode_disabled(self):
        """When progress_mode is 0, the acknowledgement page has no checklist."""
        self.scrmi.progress_mode = 0
        self.scrmi.save()
        response = self.client.get('/learn/%s/acknowledgement' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.CHECKLIST_MARKER)

    def test_mainpage_shows_checklist_when_force_show_disabled(self):
        """When force_show_required_modules is False, hitting studentreg shows
        the regular mainpage (which has its own checkboxes via context['modules']).
        The required module page itself should also show the checklist when visited
        directly (because registration_progress reads request.tl and request.program)."""
        self.scrmi.force_show_required_modules = False
        self.scrmi.save()
        # Direct visit to studentreg now shows the mainpage (no redirect)
        response = self.client.get('/learn/%s/studentreg' % self.program.url)
        self.assertEqual(response.status_code, 200)
        # The mainpage has its own checkboxes section (not from module_base.html)
        self.assertContains(response, self.CHECKLIST_MARKER)
        # Direct visit to the required module page also shows the checklist
        ack_response = self.client.get('/learn/%s/acknowledgement' % self.program.url)
        self.assertEqual(ack_response.status_code, 200)
        self.assertContains(ack_response, self.CHECKLIST_MARKER)

    def test_progress_bar_mode_shows_no_checkbox_table(self):
        """When progress_mode is 2 (progress bar), the checkbox table is absent."""
        self.scrmi.progress_mode = 2
        self.scrmi.save()
        response = self.client.get('/learn/%s/studentreg' % self.program.url)
        self.assertEqual(response.status_code, 200)
        # Progress bar mode: no "Steps for Registration" table header
        self.assertNotContains(response, self.CHECKLIST_MARKER)


class TeacherChecklistTagTest(ProgramFrameworkTest):
    """Unit tests for the teacher_checklist template tag used by
    teacher_module_base.html."""

    def setUp(self):
        super().setUp()
        self.crmi = self.program.classregmoduleinfo
        self.crmi.progress_mode = 1
        self.crmi.save()

    def _make_request(self, tl):
        request = RequestFactory().get('/')
        request.user = self.teachers[0]
        request.program = self.program
        request.tl = tl
        return request

    def test_returns_empty_outside_teacher_registration(self):
        """Shared templates render as plain pages for student and admin pages."""
        for tl in ('learn', 'manage'):
            self.assertEqual(teacher_checklist(Context({'request': self._make_request(tl)})), {})

    def test_returns_module_page_context_for_teach_tl(self):
        """Checklist links point back to the main page on teacher module pages."""
        result = teacher_checklist(Context({'request': self._make_request('teach')}))
        self.assertEqual(result['options'], self.crmi)
        self.assertEqual(result['extra_steps'], 'teach:extra_steps')
        self.assertTrue(result['is_module_page'])
        self.assertEqual(result['mainpage_url'], '/teach/%s/teacherreg' % self.program.url)
        self.assertIn('modules', result)
        self.assertIn('records', result)

    def test_reuses_checklist_from_view(self):
        """The main page passes its own checklist, which the tag must not replace."""
        checklist = {'modules': [], 'options': self.crmi}
        result = teacher_checklist(Context({'request': self._make_request('teach'), 'checklist': checklist}))
        self.assertIs(result, checklist)

    def test_looks_up_checklist_once_per_render(self):
        """teacher_module_base.html calls the tag from two blocks."""
        context = Context({'request': self._make_request('teach')})
        with mock.patch('esp.program.templatetags.modules.get_module_page_checklist_context',
                        wraps=get_module_page_checklist_context) as lookup:
            first = teacher_checklist(context)
            second = teacher_checklist(context)
        self.assertIs(first, second)
        self.assertEqual(lookup.call_count, 1)

    def _in_theme_sidebar(self, theme_name, settings):
        with mock.patch.object(ThemeController, 'get_current_theme', return_value=theme_name), \
                mock.patch.object(ThemeController, 'get_template_settings', return_value=settings):
            return teacher_checklist(Context({'request': self._make_request('teach')}))['in_theme_sidebar']

    def test_theme_sidebar_setting(self):
        """Only themes with a checklist_in_sidebar setting can move the list there."""
        self.assertTrue(self._in_theme_sidebar('bigpicture', {'checklist_in_sidebar': True}))
        self.assertFalse(self._in_theme_sidebar('bigpicture', {'checklist_in_sidebar': False}))
        # The setting can linger in the theme settings after switching themes.
        self.assertFalse(self._in_theme_sidebar('droplets', {'checklist_in_sidebar': True}))


class TeacherChecklistLayoutIntegrationTest(ProgramFrameworkTest):
    """Integration tests: teacher module pages show the checklist column."""

    SIDEBAR_MARKER = 'teacher-reg-checklist-col'

    def setUp(self):
        super().setUp()
        self.add_user_profiles()
        crmi = self.program.classregmoduleinfo
        crmi.progress_mode = 1
        crmi.save()
        self.teacher = self.teachers[0]
        self.client.login(username=self.teacher.username, password='password')

    def test_mainpage_and_module_page_show_checklist_column(self):
        for view in ('teacherreg', 'availability'):
            response = self.client.get('/teach/%s/%s' % (self.program.url, view))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, self.SIDEBAR_MARKER)
            self.assertContains(response, 'required steps done')
            self.assertContains(response, 'id="teacher-reg-checklist-steps"')

    def test_class_registration_form_has_no_checklist(self):
        response = self.client.get('/teach/%s/makeaclass' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.SIDEBAR_MARKER)
        self.assertNotContains(response, RequiredModuleProgressIntegrationTest.CHECKLIST_MARKER)

    def test_no_checklist_column_when_progress_mode_disabled(self):
        crmi = self.program.classregmoduleinfo
        crmi.progress_mode = 0
        crmi.save()
        response = self.client.get('/teach/%s/availability' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.SIDEBAR_MARKER)

    def test_bigpicture_shows_checklist_in_its_sidebar(self):
        settings = dict(ThemeController().get_template_settings(), checklist_in_sidebar=True)
        with mock.patch.object(ThemeController, 'get_current_theme', return_value='bigpicture'), \
                mock.patch.object(ThemeController, 'get_template_settings', return_value=settings):
            response = self.client.get('/teach/%s/availability' % self.program.url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertEqual(html.count(self.SIDEBAR_MARKER), 1)
        sidebar_start = html.index('id="sidebar"')
        main_start = html.index('id="main"')
        self.assertTrue(sidebar_start < html.index(self.SIDEBAR_MARKER) < main_start)
        self.assertNotIn('teacher-reg-columns', html)


class ChecklistProgressTest(SimpleTestCase):
    """Unit tests for get_checklist_progress, which feeds the checklist's progress bar."""

    @staticmethod
    def _module(completed, required=True, step=True):
        return mock.Mock(**{'isCompleted.return_value': completed,
                            'isRequired.return_value': required,
                            'isStep.return_value': step})

    def test_counts_required_steps_and_records(self):
        todo = self._module(False)
        checklist = {
            'modules': [self._module(True), todo, self._module(False, required=False),
                        self._module(False, step=False)],
            'records': [{'isCompleted': True}, {'isCompleted': False}],
        }
        progress = get_checklist_progress(checklist)
        self.assertEqual((progress['done'], progress['total'], progress['percent']), (2, 4, 50))
        self.assertIs(progress['next_step'], todo)
        self.assertIsNone(progress['next_record'])

    def test_next_record_once_steps_are_done(self):
        record = {'isCompleted': False}
        progress = get_checklist_progress({'modules': [self._module(True)], 'records': [record]})
        self.assertIsNone(progress['next_step'])
        self.assertIs(progress['next_record'], record)

    def test_records_only_without_checklist(self):
        """With the checklist off, only the other requirements are counted."""
        progress = get_checklist_progress({'modules': [self._module(False)], 'records': [{'isCompleted': True}]},
                                          include_steps=False)
        self.assertEqual((progress['done'], progress['total'], progress['percent']), (1, 1, 100))
        self.assertIsNone(progress['next_step'])
        self.assertIsNone(progress['next_record'])
