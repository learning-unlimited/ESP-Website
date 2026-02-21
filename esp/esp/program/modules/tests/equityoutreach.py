from __future__ import absolute_import

from esp.program.models import FinancialAidRequest, ProgramModule, RegistrationProfile
from esp.program.modules.handlers.equityoutreach import EquityOutreachCohorts
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import StudentInfo


class EquityOutreachModuleTest(ProgramFrameworkTest):
    def setUp(self):
        modules = [
            ProgramModule.objects.get(handler="EquityOutreachModule", module_type="manage"),
        ]
        super(EquityOutreachModuleTest, self).setUp(modules=modules, num_students=3, num_teachers=1)
        self.admin = self.admins[0]
        self.student = self.students[0]

    def _add_student_profile(self, user, transportation):
        student_info = StudentInfo.objects.create(user=user, transportation=transportation)
        profile = RegistrationProfile(user=user, program=self.program, student_info=student_info)
        profile.save()

    def test_cohort_queries(self):
        self._add_student_profile(self.student, "Public bus is difficult")
        FinancialAidRequest.objects.create(program=self.program, user=self.student, done=False)

        transportation_users = EquityOutreachCohorts.users_for_cohort(
            self.program, EquityOutreachCohorts.COHORT_TRANSPORTATION_BARRIER
        )
        finaid_users = EquityOutreachCohorts.users_for_cohort(
            self.program, EquityOutreachCohorts.COHORT_INCOMPLETE_FINAID
        )

        self.assertIn(self.student, list(transportation_users))
        self.assertIn(self.student, list(finaid_users))

    def test_equity_lists_in_program_lists(self):
        """Equity cohorts are exposed as student lists for Communications Panel / User Records."""
        pm = self.program.getModule("EquityOutreachModule")
        lists = pm.students(QObject=False)
        descs = pm.studentDesc()

        for key in EquityOutreachCohorts.all_cohort_keys():
            list_name = "equity_" + key
            self.assertIn(list_name, lists)
            self.assertIn(list_name, descs)
            self.assertEqual(descs[list_name], EquityOutreachCohorts.cohort_label(key))

