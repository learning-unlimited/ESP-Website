from __future__ import absolute_import

from esp.dbmail.models import MessageRequest
from esp.program.models import EquityOutreachCampaign, EquityOutreachRecipient, FinancialAidRequest, ProgramModule, RegistrationProfile
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

    def test_email_campaign_creates_message_request_and_snapshot(self):
        self._add_student_profile(self.student, "Bus")
        FinancialAidRequest.objects.create(program=self.program, user=self.student, done=False)

        self.assertTrue(self.client.login(username=self.admin.username, password="password"))
        response = self.client.post(
            "/manage/%s/equityoutreach_send" % self.program.getUrlBase(),
            {
                "cohort_key": EquityOutreachCohorts.COHORT_INCOMPLETE_FINAID,
                "channel": "email",
                "subject": "Need help finishing aid",
                "body": "Please complete your financial aid form.",
            },
        )
        self.assertEqual(response.status_code, 200)

        campaign = EquityOutreachCampaign.objects.get(program=self.program, channel=EquityOutreachCampaign.CHANNEL_EMAIL)
        self.assertEqual(campaign.recipient_count, 1)
        self.assertEqual(campaign.success_count, 1)
        self.assertEqual(campaign.failure_count, 0)
        self.assertIsNotNone(campaign.message_request)

        msg_request = MessageRequest.objects.get(id=campaign.message_request_id)
        self.assertEqual(msg_request.subject, "Need help finishing aid")

        recipients = EquityOutreachRecipient.objects.filter(campaign=campaign)
        self.assertEqual(recipients.count(), 1)
        self.assertEqual(recipients[0].status, EquityOutreachRecipient.STATUS_QUEUED)

