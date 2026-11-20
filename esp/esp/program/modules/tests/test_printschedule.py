"""Regression tests for #6280: OnsiteClassSchedule.printschedule."""
from esp.program.tests import ProgramFrameworkTest
from esp.utils.models import Printer, PrintRequest


class PrintScheduleTest(ProgramFrameworkTest):
    def setUp(self):
        super().setUp(num_students=2, num_teachers=1, classes_per_teacher=1)
        self.add_user_profiles()
        self.student, self.other_student = self.students[:2]
        self.admin = self.admins[0]
        self.url = '/onsite/%s/printschedule' % self.program.getUrlBase()
        self.default_next = '/learn/%s/studentreg' % self.program.getUrlBase()

    def login(self, user):
        self.assertTrue(self.client.login(username=user.username, password='password'))

    def test_get_does_not_create_print_request(self):
        self.login(self.student)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)
        self.assertFalse(PrintRequest.objects.exists())

    def test_post_creates_request_for_self_and_redirects_to_default(self):
        self.login(self.student)
        response = self.client.post(self.url)
        self.assertRedirects(response, self.default_next, fetch_redirect_response=False)
        self.assertEqual(list(PrintRequest.objects.values_list('user_id', flat=True)), [self.student.id])

    def test_next_on_same_site_is_followed(self):
        self.login(self.student)
        response = self.client.post(self.url + '?next=/manage/userview?username=x')
        self.assertRedirects(response, '/manage/userview?username=x', fetch_redirect_response=False)

    def test_next_to_other_site_is_ignored(self):
        self.login(self.student)
        for bad in ('https://example.com', '//example.com/x', 'javascript:alert(1)'):
            response = self.client.post(self.url, {}, QUERY_STRING='next=' + bad)
            self.assertRedirects(response, self.default_next, fetch_redirect_response=False)

    def test_student_cannot_print_for_another_user(self):
        self.login(self.student)
        response = self.client.post(self.url + '?user=%d' % self.other_student.id)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(PrintRequest.objects.exists())

    def test_student_can_name_themselves_in_user_param(self):
        self.login(self.student)
        response = self.client.post(self.url + '?user=%d' % self.student.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PrintRequest.objects.get().user_id, self.student.id)

    def test_admin_can_print_for_another_user(self):
        self.login(self.admin)
        response = self.client.post(self.url + '?user=%d' % self.student.id)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PrintRequest.objects.get().user_id, self.student.id)

    def test_unknown_printer_is_404(self):
        self.login(self.student)
        response = self.client.post(self.url + '?printer=doesnotexist')
        self.assertEqual(response.status_code, 404)
        self.assertFalse(PrintRequest.objects.exists())

    def test_known_printer_is_used(self):
        printer = Printer.objects.create(name='Front Desk')
        self.login(self.student)
        response = self.client.post(self.url + '?printer=Front Desk')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(PrintRequest.objects.get().printer, printer)
