"""
Tests for the lottery gates in the required-module flow: the student lottery
(phase zero) holds students until they are selected, and the class lottery
(two-phase) holds them until it closes, and the registration checklist says so.
"""

from datetime import datetime, timedelta

from django.contrib.auth.models import Group

from esp.program.models import PhaseZeroRecord
from esp.program.modules.base import ProgramModuleObj
from esp.program.modules.tests.studentregtwophase import StudentRegTwoPhaseBaseTest
from esp.tagdict.models import Tag
from esp.users.models import Permission


class LotteryGateTest(StudentRegTwoPhaseBaseTest):
    """A program with both lotteries as required modules, forced in order."""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.phasezero = self._module('StudentRegPhaseZero')
        self.twophase = self._module('StudentRegTwoPhase')
        for pmo in (self.phasezero, self.twophase):
            pmo.required = True
            pmo.save()
        scrmi = self.program.studentclassregmoduleinfo
        scrmi.force_show_required_modules = True
        scrmi.save()
        Tag.setTag('student_lottery_group_max', target=self.program, value='1')
        Permission.objects.get_or_create(role=Group.objects.get(name='Student'),
                                         permission_type='Student/PhaseZero', program=self.program)
        self.student = self.students[0]
        self.assertTrue(self.client.login(username=self.student.username, password='password'))
        self.studentreg = '/learn/%s/studentreg' % self.program.getUrlBase()

    def _module(self, handler):
        return ProgramModuleObj.objects.get(program=self.program, module__handler=handler)

    def _gate_status(self, handler):
        """gate_status from the module's handler class, as findModule sees it."""
        module = next(m for m in self.program.getModules() if m.module.handler == handler)
        return module.gate_status(self.student)

    def _enter_student_lottery(self):
        record = PhaseZeroRecord.objects.create(program=self.program)
        record.user.add(self.student)

    def _select_student(self):
        Permission.objects.create(user=self.student, permission_type='OverridePhaseZero', program=self.program)

    def _close(self, pmo):
        pmo.end_date = datetime.now() - timedelta(hours=1)
        pmo.save()

    def test_student_lottery_holds_students_who_have_entered(self):
        self._enter_student_lottery()
        self.assertEqual(self._gate_status('StudentRegPhaseZero'), 'waiting')
        response = self.client.get(self.studentreg)
        self.assertContains(response, 'This is confirmation that you are entered into our student lottery')
        self.assertContains(response, "You're entered in the student lottery")
        self.assertContains(response, 'After the student lottery')

    def test_student_lottery_still_holds_unselected_students_once_closed(self):
        """Closing phase zero must not let students who weren't selected through."""
        self._enter_student_lottery()
        Tag.setTag('student_lottery_run', target=self.program, value='True')
        self._close(self.phasezero)
        response = self.client.get(self.studentreg)
        self.assertContains(response, 'not selected')
        self.assertContains(response, "You weren't selected in the student lottery")
        # The steps after the lottery are hidden from students who can't take them.
        self.assertNotContains(response, 'Two-Phase Student Registration')

    def test_selected_students_reach_the_class_lottery(self):
        self._enter_student_lottery()
        self._select_student()
        response = self.client.get(self.studentreg)
        self.assertContains(response, 'Star all classes you are interested in taking')
        self.assertContains(response, 'Submit my preferences')

    def test_submitting_class_preferences_keeps_students_at_the_class_lottery(self):
        self._select_student()
        self.client.post('/learn/%s/confirm_registration' % self.program.getUrlBase())
        self.assertEqual(self._gate_status('StudentRegTwoPhase'), 'waiting')
        response = self.client.get(self.studentreg)
        self.assertContains(response, 'Star all classes you are interested in taking')
        self.assertContains(response, "You're all set until the class lottery")
        self.assertContains(response, 'Email me an updated summary')

    def test_class_lottery_holds_students_before_it_opens(self):
        self._select_student()
        self.twophase.start_date = datetime.now() + timedelta(days=1)
        self.twophase.save()
        self.assertEqual(self._gate_status('StudentRegTwoPhase'), 'waiting')
        response = self.client.get(self.studentreg)
        self.assertNotContains(response, 'Student registration for')

    def test_closing_the_class_lottery_lets_students_through(self):
        self._select_student()
        self._close(self.twophase)
        self.assertEqual(self._gate_status('StudentRegTwoPhase'), 'passed')
        response = self.client.get(self.studentreg)
        self.assertContains(response, 'Student registration for')
        self.assertContains(response, 'Two-Phase Student Registration')
        self.assertContains(response, '(closed)')


class ScheduledRequiredModuleTest(StudentRegTwoPhaseBaseTest):
    """Required modules outside their schedule window aren't forced, but are
    still listed in the checklist."""

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.ack = ProgramModuleObj.objects.get(program=self.program, module__handler='StudentAcknowledgementModule')
        self.ack.required = True
        scrmi = self.program.studentclassregmoduleinfo
        scrmi.force_show_required_modules = True
        scrmi.save()
        student = self.students[0]
        self.assertTrue(self.client.login(username=student.username, password='password'))
        self.studentreg = '/learn/%s/studentreg' % self.program.getUrlBase()

    def test_open_required_module_is_forced(self):
        self.ack.save()
        response = self.client.get(self.studentreg)
        self.assertNotContains(response, 'Student registration for')

    def test_closed_required_module_is_listed_as_closed(self):
        self.ack.end_date = datetime.now() - timedelta(hours=1)
        self.ack.save()
        response = self.client.get(self.studentreg)
        self.assertContains(response, 'Student registration for')
        self.assertContains(response, 'Student Acknowledgement <i>(closed)</i>', html=False)

    def test_upcoming_required_module_is_listed_with_its_opening_date(self):
        self.ack.start_date = datetime(2099, 3, 14)
        self.ack.save()
        response = self.client.get(self.studentreg)
        self.assertContains(response, 'Student registration for')
        self.assertContains(response, 'Opens Mar 14')
