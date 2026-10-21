"""
Tests for the "I don't need financial aid" option of the financial aid
application, which lets students complete that step without applying.
"""

from esp.program.models import FinancialAidRequest
from esp.program.modules.base import ProgramModuleObj
from esp.program.modules.handlers.financialaidappmodule import FinancialAidAppModule
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import Record


class FinancialAidDeclineTest(ProgramFrameworkTest):

    def setUp(self, *args, **kwargs):
        super().setUp(*args, **kwargs)
        self.add_user_profiles()
        self.student = self.students[0]
        self.assertTrue(self.client.login(username=self.student.username, password='password'))
        self.finaid_url = '/learn/%s/finaid' % self.program.getUrlBase()
        self.studentreg = '/learn/%s/studentreg' % self.program.getUrlBase()

    def _module(self):
        return self.program.getModule('FinancialAidAppModule')

    def _decline(self):
        return self.client.post(self.finaid_url, {'submitform': FinancialAidAppModule.DECLINE_LABEL})

    def test_declining_completes_the_step_without_an_application(self):
        response = self._decline()
        self.assertEqual(response.status_code, 302)
        self.assertIn(self.studentreg, response['Location'])
        self.assertTrue(self._module().isCompleted(self.student))
        self.assertFalse(FinancialAidRequest.objects.filter(user=self.student, program=self.program).exists())

    def test_page_offers_declining_until_the_student_applies(self):
        response = self.client.get(self.finaid_url, secure=True)
        self.assertContains(response, "Don't need financial aid?")
        self._decline()
        response = self.client.get(self.finaid_url, secure=True)
        self.assertContains(response, "You've told us you don't need financial aid")
        self.client.post(self.finaid_url, {'household_income': '12345', 'submitform': 'Complete'})
        response = self.client.get(self.finaid_url, secure=True)
        self.assertNotContains(response, "Don't need financial aid?")
        self.assertNotContains(response, "You've told us you don't need financial aid")

    def test_applying_replaces_a_decline(self):
        self._decline()
        self.client.post(self.finaid_url, {'household_income': '12345', 'submitform': 'Complete'})
        self.assertFalse(Record.user_completed(self.student, FinancialAidAppModule.DECLINED_EVENT, self.program))
        self.assertTrue(self.student.appliedFinancialAid(self.program))
        self.assertTrue(self._module().isCompleted(self.student))

    def test_required_financial_aid_can_be_declined_to_continue(self):
        for pmo in self.program.getModules():
            pmo.__class__ = ProgramModuleObj
            pmo.required = pmo.module.handler == 'FinancialAidAppModule'
            pmo.save()
        scrmi = self.program.studentclassregmoduleinfo
        scrmi.force_show_required_modules = True
        scrmi.save()

        response = self.client.get(self.studentreg, secure=True)
        self.assertContains(response, 'Financial Aid Request Form')
        self._decline()
        response = self.client.get(self.studentreg, secure=True)
        self.assertNotContains(response, 'Financial Aid Request Form')
        self.assertContains(response, 'Student registration for')
