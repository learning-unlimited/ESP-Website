"""Later steps of multi-step admin tools, opened directly, go back to the first step.

Their error messages for stale or incomplete submissions are not logged as
server errors (which would email the server log).
"""

from django.db.models import Q

from esp.program.models import PrintableJob
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, PersistentQueryFilter

ERROR_LOGGER = 'esp.middleware.esperrormiddleware'


class FinalStepRedirectTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp()
        self.client.login(username=self.admins[0].username, password='password')
        self.manage_url = self.program.get_manage_url()

    def test_opening_a_later_step_directly_redirects_to_the_first_step(self):
        steps = {
            'batchclassregfinal': 'batchclassreg',
            'filter_permission_final': 'filter_permission',
            'grouptextfinal': 'grouptextpanel',
            'usergroupfinal': 'usergroup',
            'userrecordsfinal': 'userrecords',
            'deactivatefinal': 'deactivate',
            'commprev': 'commpanel',
            'commfinal': 'commpanel',
            'maincomm2': 'commpanel',
        }
        for view, first_step in steps.items():
            with self.subTest(view=view):
                response = self.client.get(f'{self.manage_url}{view}?filterid=1')
                self.assertRedirects(response, f'{self.manage_url}{first_step}', fetch_redirect_response=False)

    def test_incomplete_submission_is_not_logged_as_a_server_error(self):
        with self.assertNoLogs(ERROR_LOGGER, level='ERROR'):
            response = self.client.post(f'{self.manage_url}userrecordsfinal', {})
        self.assertTemplateUsed(response, 'error.html')
        self.assertContains(response, 'User filter has not been properly set', status_code=500)

    def test_filter_matching_no_users_is_not_logged_as_a_server_error(self):
        empty = PersistentQueryFilter.create_from_Q(ESPUser, Q(username='no-such-user'))
        with self.assertNoLogs(ERROR_LOGGER, level='ERROR'):
            response = self.client.post(f'{self.manage_url}usergroupfinal?filterid={empty.id}',
                                        {'group_name_new': 'final_step_test_group'})
        self.assertTemplateUsed(response, 'error.html')
        self.assertContains(response, 'Your query did not match any users', status_code=500)

    def test_unknown_printable_job_is_not_logged_as_a_server_error(self):
        self.assertFalse(PrintableJob.objects.filter(id=999999).exists())
        with self.assertNoLogs(ERROR_LOGGER, level='ERROR'):
            response = self.client.get(f'{self.manage_url}printable_job_status/999999/')
        self.assertTemplateUsed(response, 'error.html')
        self.assertContains(response, 'Job not found.', status_code=500)
