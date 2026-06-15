from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser, StudentInfo, Record, RecordType
from esp.program.models import RegistrationProfile
from esp.users.controllers.usersearch import UserSearchController


class TestUserSearchController(ProgramFrameworkTest):

    def setUp(self):
        super(TestUserSearchController, self).setUp()
        self.add_user_profiles()
        self.controller = UserSearchController()

    def _get_combination_post_data(self, list_a, list_b):
        return {
            'username': '',
            'checkbox_and_teacher_profile': '',
            'first_name': '',
            'last_name': '',
            'school': '',
            'use_checklist': '0',
            'gradyear_max': '',
            'userid': '',
            'zipcode': '',
            'combo_base_list': f'{list_a}:{list_b}',
            'email': '',
            'states': '',
            'zipdistance': '',
            'grade_min': '',
            'gradyear_min': '',
            'checkbox_and_class_approved': '',
            'grade_max': '',
            'student_sendto_self': '1',
            'zipdistance_exclude': '',
        }

    def test_student_confirmed(self):
        post_data = self._get_combination_post_data('Student', 'confirmed')
        query_result = self.controller.filter_from_postdata(self.program, post_data).getList(ESPUser)
        self.assertEqual(query_result.model, ESPUser)
        self.assertGreaterEqual(query_result.count(), 0)

    def test_teacher_interview(self):
        post_data = self._get_combination_post_data('Teacher', 'Teacher Interview')
        query_result = self.controller.filter_from_postdata(self.program, post_data).getList(ESPUser)
        self.assertEqual(query_result.model, ESPUser)
        self.assertGreaterEqual(query_result.count(), 0)

    def test_teacher_classroom_tables_query_from_post(self):
        post_data = self._get_combination_post_data('Teacher', 'allTeacher')
        query = self.controller.query_from_postdata(self.program, post_data)
        self.assertIsNotNone(query)
        result = ESPUser.objects.filter(query)
        self.assertEqual(result.model, ESPUser)
        self.assertGreater(result.count(), 0)

    def test_overlap_bug(self):
        """
        Verify that combining mutually exclusive checklist filters (e.g., 'attended' AND
        'confirmed') using the combo_base_list intersection strategy does not result in a
        single row failing the AND condition, and instead properly intersects the subsets.
        Issue #956
        """
        # Base list: Student Profile
        post_data = self._get_combination_post_data('Student', 'student_profile')
        # Add AND filters for both 'attended' and 'confirmed'
        post_data['checkbox_and_attended'] = '1'
        post_data['checkbox_and_confirmed'] = '1'

        # Create test user
        test_user = self.students[0]  # Use existing test student from ProgramFrameworkTest

        # Setup RecordTypes
        rt_attended, _ = RecordType.objects.get_or_create(name='attended', defaults={'description': 'Attended'})
        rt_confirmed, _ = RecordType.objects.get_or_create(name='reg_confirmed', defaults={'description': 'Registration Confirmed'})

        # Create records for the same user
        Record.objects.create(user=test_user, event=rt_attended, program=self.program)
        Record.objects.create(user=test_user, event=rt_confirmed, program=self.program)

        # Create another user with only ONE record to ensure exclusion
        other_user = ESPUser.objects.create_user(username='otheruser', email='other@example.com', password='password')
        other_user.makeRole("Student")
        student_info = StudentInfo.objects.create(user=other_user, graduation_year=ESPUser.program_schoolyear(self.program)+2)
        RegistrationProfile.objects.create(user=other_user, program=self.program, student_info=student_info, most_recent_profile=True)
        Record.objects.create(user=other_user, event=rt_attended, program=self.program)

        query = self.controller.query_from_postdata(self.program, post_data)
        results = ESPUser.objects.filter(query).distinct()

        # The test_user should be found because they have BOTH records
        self.assertIn(test_user, results)
        # The other_user should NOT be found because they only have ONE of the records (AND logic)
        self.assertNotIn(other_user, results)
        self.assertEqual(results.count(), 1)

    def test_all_base_list_or_overlap(self):
        """
        Verify that using 'all_X' as the combo_base_list correctly seeds q_program
        with ESPUser.getAllOfType() instead of an empty Q(), so that OR conditions
        correctly produce a union rather than an intersection.

        Before the fix: Q() | Q(class_approved) collapsed to just Q(class_approved),
        making "All teachers OR class_approved teachers" return only teachers with
        an approved class — incorrectly excluding teachers without one.

        After the fix: ESPUser.getAllOfType('Teacher') | Q(class_approved) correctly
        returns ALL teachers in the DB regardless of whether they have an approved class.

        Issue #1655
        """
        # teacher_only: in the Teacher group, but has NO approved class
        teacher_only = ESPUser.objects.create_user(
            username='teacher_only_1655', email='tonly@example.com', password='password')
        teacher_only.makeRole('Teacher')

        # teacher_submitted: in the Teacher group AND has a proposed class
        teacher_submitted = ESPUser.objects.create_user(
            username='teacher_submitted_1655', email='tsub@example.com', password='password')
        teacher_submitted.makeRole('Teacher')

        # Create a class for teacher_submitted so they appear in class_submitted
        from esp.program.models import ClassSubject
        cls = ClassSubject.objects.create(
            parent_program=self.program,
            status=0,   # proposed status
            category=self.program.class_categories.first(),
            grade_min=7, grade_max=12,
            class_size_max=20,
            duration=1.0,
            title='Test Class',
        )
        cls.teachers.add(teacher_submitted)

        # Confirm class_submitted list includes teacher_submitted but NOT teacher_only
        teacher_lists = self.program.teachers(QObjects=True)
        submitted_qs = ESPUser.objects.filter(teacher_lists['class_submitted']).distinct()
        self.assertIn(teacher_submitted, submitted_qs)
        self.assertNotIn(teacher_only, submitted_qs)

        # Submit: base list = all_Teacher, OR = class_submitted
        post_data = self._get_combination_post_data('Teacher', 'all_Teacher')
        post_data['checkbox_or_class_submitted'] = '1'

        query = self.controller.query_from_postdata(self.program, post_data)
        results = ESPUser.objects.filter(query).distinct()

        # Both teachers must be in results because the base list is ALL teachers.
        # Before the fix, only teacher_submitted would be returned (erroneous AND behavior).
        self.assertIn(teacher_only, results,
            "teacher_only should be included via the all_Teacher base list")
        self.assertIn(teacher_submitted, results,
            "teacher_submitted should be included via both the base list and the OR condition")
