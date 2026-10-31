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
from esp.program.modules.checklist import get_checklist_context, get_checklist_progress, get_module_page_checklist_context
from esp.program.templatetags.modules import registration_checklist
from esp.program.tests import ProgramFrameworkTest
from esp.themes.controllers import ThemeController


class RegistrationChecklistTagTest(ProgramFrameworkTest):
    """Unit tests for the registration_checklist template tag used by
    module_base.html.

    These tests call the tag function directly using a RequestFactory-built
    request, so no URL routing or permission setup is required.
    """

    def setUp(self):
        super().setUp()
        self.scrmi = self.program.studentclassregmoduleinfo
        self.scrmi.show_checklist = True
        self.scrmi.save()
        self.crmi = self.program.classregmoduleinfo
        self.crmi.show_checklist = True
        self.crmi.save()

    def _make_request(self, tl=None, with_program=True):
        request = RequestFactory().get('/')
        request.user = self.teachers[0] if tl == 'teach' else self.students[0]
        if with_program:
            request.program = self.program
        if tl is not None:
            request.tl = tl
        return request

    def _checklist(self, tl=None, with_program=True, **extra):
        return registration_checklist(Context(dict(extra, request=self._make_request(tl, with_program))))

    def test_returns_empty_without_request_in_context(self):
        self.assertEqual(registration_checklist(Context({})), {})

    def test_returns_empty_without_program_on_request(self):
        self.assertEqual(self._checklist('learn', with_program=False), {})

    def test_returns_empty_outside_registration(self):
        """Shared templates render as plain pages without a tl or for admin pages."""
        for tl in (None, 'manage'):
            self.assertEqual(self._checklist(tl), {})

    def test_returns_module_page_context(self):
        """Checklist links point back to the main page on module pages."""
        for tl, options, mainpage in (('learn', self.scrmi, 'studentreg'), ('teach', self.crmi, 'teacherreg')):
            result = self._checklist(tl)
            self.assertEqual(result['options'], options)
            self.assertEqual(result['extra_steps'], '%s:extra_steps' % tl)
            self.assertEqual(result['program'], self.program)
            self.assertTrue(result['is_module_page'])
            self.assertEqual(result['mainpage_url'], '/%s/%s/%s' % (tl, self.program.url, mainpage))
            self.assertIn('modules', result)
            self.assertIn('records', result)
            self.assertTrue(result['show_list'])

    def test_no_list_when_checklist_disabled(self):
        self.scrmi.show_checklist = False
        self.scrmi.save()
        self.assertFalse(self._checklist('learn')['show_list'])

    def test_completedAll_false_when_required_module_incomplete(self):
        """completedAll is False when a required module has not been completed."""
        # Make StudentAcknowledgementModule required for this program
        pm = ProgramModule.objects.get(handler='StudentAcknowledgementModule')
        pmo = ProgramModuleObj.getFromProgModule(self.program, pm)
        pmo.__class__ = ProgramModuleObj
        pmo.required = True
        pmo.save()
        # student0 has not submitted the acknowledgement, so completedAll should be False
        self.assertFalse(self._checklist('learn')['completedAll'])

    def test_completedAll_true_when_no_required_modules(self):
        """completedAll is True when no required modules exist for the program."""
        # Make all modules non-required
        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = False
            pmo.save()
        self.assertTrue(self._checklist('learn')['completedAll'])

    def test_reuses_checklist_from_view(self):
        """The main pages pass their own checklist, which the tag must not replace."""
        checklist = {'modules': [], 'options': self.crmi, 'completedAll': True, 'program': self.program}
        self.assertIs(self._checklist('teach', checklist=checklist), checklist)

    def test_view_can_turn_off_checklist(self):
        """The student main page passes an empty checklist for onsite registration."""
        self.assertEqual(self._checklist('learn', checklist={}), {})

    def test_looks_up_checklist_once_per_render(self):
        """module_base.html calls the tag from two blocks."""
        context = Context({'request': self._make_request('teach')})
        with mock.patch('esp.program.templatetags.modules.get_module_page_checklist_context',
                        wraps=get_module_page_checklist_context) as lookup:
            first = registration_checklist(context)
            second = registration_checklist(context)
        self.assertIs(first, second)
        self.assertEqual(lookup.call_count, 1)

    def _in_theme_sidebar(self, theme_name, settings):
        with mock.patch.object(ThemeController, 'get_current_theme', return_value=theme_name), \
                mock.patch.object(ThemeController, 'get_template_settings', return_value=settings):
            return self._checklist('teach')['in_theme_sidebar']

    def test_theme_sidebar_setting(self):
        """Only themes with a checklist_in_sidebar setting can move the list there."""
        self.assertTrue(self._in_theme_sidebar('bigpicture', {'checklist_in_sidebar': True}))
        self.assertFalse(self._in_theme_sidebar('bigpicture', {'checklist_in_sidebar': False}))
        # The setting can linger in the theme settings after switching themes.
        self.assertFalse(self._in_theme_sidebar('droplets', {'checklist_in_sidebar': True}))


class RequiredModuleProgressIntegrationTest(ProgramFrameworkTest):
    """Integration tests: student registration pages show the checklist.

    These tests use the Django test client to make full HTTP requests.
    The program is set up with StudentAcknowledgementModule as the only
    required module, force_show_required_modules=True, and the checklist
    turned on.

    The test student has Student/All permission (set up by ProgramFrameworkTest)
    so they can reach all student-facing module pages.
    """

    # Text that appears in the checklist table header (checkboxes.html)
    CHECKLIST_MARKER = 'Steps for Registration'
    SIDEBAR_MARKER = 'reg-checklist-col'

    def setUp(self):
        super().setUp()
        self.add_user_profiles()

        # Make only StudentAcknowledgementModule required; silence all others
        ack_pm = ProgramModule.objects.get(handler='StudentAcknowledgementModule')
        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = (pmo.module == ack_pm)
            pmo.save()

        # Enable the required-module redirect flow with the checklist
        self.scrmi = self.program.studentclassregmoduleinfo
        self.scrmi.force_show_required_modules = True
        self.scrmi.show_checklist = True
        self.scrmi.save()

        # Log in as the first test student
        self.student = self.students[0]
        self.client.login(username=self.student.username, password='password')

    def test_required_module_page_shows_progress_checklist(self):
        """Visiting studentreg with an incomplete required module should
        serve the required module page including the registration checklist."""
        response = self.client.get('/learn/%s/studentreg' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.SIDEBAR_MARKER)
        self.assertContains(response, self.CHECKLIST_MARKER)

    def test_steps_are_not_links_while_required_modules_are_forced(self):
        """Students shouldn't be able to click past the required modules."""
        response = self.client.get('/learn/%s/studentreg' % self.program.url)
        self.assertContains(response, 'Student Acknowledgement')
        self.assertNotContains(response, 'class="vModuleLink"')

    def test_no_checklist_when_checklist_disabled(self):
        """With the checklist turned off, the acknowledgement page has none."""
        self.scrmi.show_checklist = False
        self.scrmi.save()
        response = self.client.get('/learn/%s/acknowledgement' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.CHECKLIST_MARKER)
        self.assertNotContains(response, self.SIDEBAR_MARKER)

    def test_mainpage_shows_checklist_when_force_show_disabled(self):
        """When force_show_required_modules is False, hitting studentreg shows
        the main page, with the checklist column and linked steps.  The
        required module page itself also shows the checklist when visited
        directly (because registration_checklist reads request.tl and
        request.program)."""
        self.scrmi.force_show_required_modules = False
        self.scrmi.save()
        response = self.client.get('/learn/%s/studentreg' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Student registration for')
        self.assertContains(response, self.SIDEBAR_MARKER)
        self.assertContains(response, 'registration requirements done')
        self.assertContains(response, 'class="vModuleLink"')
        ack_response = self.client.get('/learn/%s/acknowledgement' % self.program.url)
        self.assertEqual(ack_response.status_code, 200)
        self.assertContains(ack_response, self.SIDEBAR_MARKER)

    def test_class_pages_have_no_checklist(self):
        """Pages students open on purpose to pick classes show no checklist."""
        self.scrmi.force_show_required_modules = False
        self.scrmi.save()
        cls = self.program.classes()[0]
        timeslot = self.program.getTimeSlots()[0]
        for view in ('fillslot/%d' % timeslot.id, 'class_docs/%d' % cls.id):
            response = self.client.get('/learn/%s/%s' % (self.program.url, view))
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, self.SIDEBAR_MARKER)
            self.assertNotContains(response, self.CHECKLIST_MARKER)


class TeacherChecklistLayoutIntegrationTest(ProgramFrameworkTest):
    """Integration tests: teacher module pages show the checklist column."""

    SIDEBAR_MARKER = RequiredModuleProgressIntegrationTest.SIDEBAR_MARKER

    def setUp(self):
        super().setUp()
        self.add_user_profiles()
        crmi = self.program.classregmoduleinfo
        crmi.show_checklist = True
        crmi.save()
        self.teacher = self.teachers[0]
        self.client.login(username=self.teacher.username, password='password')

    def test_mainpage_and_module_page_show_checklist_column(self):
        for view in ('teacherreg', 'availability'):
            response = self.client.get('/teach/%s/%s' % (self.program.url, view))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, self.SIDEBAR_MARKER)
            self.assertContains(response, 'registration requirements done')
            self.assertContains(response, 'id="reg-checklist-steps"')

    def test_class_registration_form_has_no_checklist(self):
        response = self.client.get('/teach/%s/makeaclass' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, self.SIDEBAR_MARKER)
        self.assertNotContains(response, RequiredModuleProgressIntegrationTest.CHECKLIST_MARKER)

    def test_class_tool_pages_have_no_checklist(self):
        cls = self.teacher.getTaughtClasses(self.program)[0]
        for view in ('copyclasses', 'class_status/%d' % cls.id, 'coteachers?clsid=%d' % cls.id):
            response = self.client.get('/teach/%s/%s' % (self.program.url, view))
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, self.SIDEBAR_MARKER)
            self.assertNotContains(response, RequiredModuleProgressIntegrationTest.CHECKLIST_MARKER)

    def test_no_checklist_column_when_checklist_disabled(self):
        crmi = self.program.classregmoduleinfo
        crmi.show_checklist = False
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
        self.assertNotIn('reg-columns', html)

    def _require_acknowledgement(self, force_show):
        """Make the (unfinished) teacher acknowledgement a required step."""
        pm = ProgramModule.objects.get(handler='TeacherAcknowledgementModule')
        pmo = ProgramModuleObj.getFromProgModule(self.program, pm)
        pmo.__class__ = ProgramModuleObj
        pmo.required = True
        pmo.save()
        scrmi = self.program.studentclassregmoduleinfo
        scrmi.force_show_required_modules = force_show
        scrmi.save()

    def test_steps_are_not_links_while_required_modules_are_forced(self):
        """Teachers shouldn't be able to click past the required modules."""
        self._require_acknowledgement(force_show=True)
        response = self.client.get('/teach/%s/availability' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Teacher Acknowledgement')
        self.assertNotContains(response, 'class="vModuleLink"')

    def test_steps_are_links_when_required_modules_are_not_forced(self):
        self._require_acknowledgement(force_show=False)
        response = self.client.get('/teach/%s/availability' % self.program.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="vModuleLink"')


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


class ChecklistOrderTest(SimpleTestCase):
    """The checklist lists modules in the order users meet them."""

    @staticmethod
    def _module(seq, required, completed=False):
        return mock.Mock(seq=seq, **{'isRequired.return_value': required,
                                     'isCompleted.return_value': completed})

    def _order(self, forced):
        prog = mock.Mock()
        prog.studentclassregmoduleinfo.force_show_required_modules = forced
        modules = [self._module(4, False), self._module(20, True, completed=True),
                   self._module(0, True), self._module(35, False, completed=True)]
        with mock.patch('esp.program.modules.handlers.studentregcore.StudentRegCore.get_reg_records', return_value=[]):
            checklist = get_checklist_context(mock.Mock(), prog, 'learn', modules)
        return [m.seq for m in checklist['modules']]

    def test_required_modules_first_when_forced(self):
        self.assertEqual(self._order(forced=True), [0, 20, 4, 35])

    def test_seq_order_when_not_forced(self):
        """Finished modules aren't moved to the top."""
        self.assertEqual(self._order(forced=False), [0, 4, 20, 35])
