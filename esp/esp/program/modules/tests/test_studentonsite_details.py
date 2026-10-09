from esp.program.models import ProgramModule, StudentRegistration
from esp.program.tests import ProgramFrameworkTest

# ProgramFrameworkTest enables every module by default, and some required ones
# (the lottery, the medical form) take over the page for a student who hasn't
# completed them. Only enable what the onsite pages need, so these tests reach
# the onsite view itself.
ONSITE_MODULES = ['StudentOnsite', 'StudentClassRegModule', 'StudentRegCore']


class StudentOnsiteDetailsSectionIdTest(ProgramFrameworkTest):

    def setUp(self):
        super().setUp(
            num_students=1, num_teachers=1, classes_per_teacher=1,
            modules=ProgramModule.objects.filter(handler__in=ONSITE_MODULES),
        )
        self.add_student_profiles()
        self.schedule_randomly()
        self.student = self.students[0]
        self.section = self.program.sections().first()
        self.schedule_url = self.program.get_learn_url() + 'studentonsite'
        self.assertTrue(self.client.login(username=self.student.username, password='password'))

    def details(self, extra=None):
        url = self.program.get_learn_url() + 'onsitedetails'
        if extra is not None:
            url += '/' + extra
        return self.client.get(url)

    def assert_redirects_to_schedule(self, response, msg=''):
        self.assertRedirects(response, self.schedule_url, fetch_redirect_response=False, msg_prefix=msg)

    def test_enrolled_section_shows_section_info(self):
        self.section.preregister_student(self.student, fast_force_create=True)
        response = self.details(str(self.section.id))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'program/modules/studentonsite/sectioninfo.html')
        self.assertEqual(response.context['section'], self.section)

    def test_section_student_is_not_enrolled_in_redirects(self):
        self.assert_redirects_to_schedule(self.details(str(self.section.id)))

    def test_missing_section_id_redirects(self):
        self.assert_redirects_to_schedule(self.details())

    def test_unknown_numeric_section_id_redirects(self):
        for extra in ('999999', '0', '-1'):
            self.assert_redirects_to_schedule(self.details(extra), 'extra=%r: ' % extra)

    def test_non_numeric_section_id_redirects(self):
        for extra in ('abc', '12abc', '0x10', '1e5', '1_000'):
            self.assert_redirects_to_schedule(self.details(extra), 'extra=%r: ' % extra)

    def test_out_of_range_section_id_redirects(self):
        self.assert_redirects_to_schedule(self.details('99999999999999999999'))
