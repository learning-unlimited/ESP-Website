from __future__ import absolute_import
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.tests.util import user_role_setup
from esp.users.forms.user_reg import ValidHostEmailField
from esp.users.models import User, ESPUser, UserForwarder, StudentInfo, Permission, Record, RecordType
from django.test import TestCase
import esp.users.views as views
from esp.program.models import Program, RegistrationProfile

import random
import string

#python manage.py test users.controllers.tests.test_usersearch:TestUserSearchController.test_overlap_bug

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

<<<<<<< HEAD
    def test_username_exact_match(self):
        """Username search should use iexact (not substring) matching."""
        User.objects.create_user(username='john', password='x')
        User.objects.create_user(username='johnny', password='x')

        query = UserSearchController().query_from_criteria(
            'any', {'username': 'john'}
        )
        results = User.objects.filter(query)
        usernames = list(results.values_list('username', flat=True))
        self.assertIn('john', usernames)
        self.assertNotIn('johnny', usernames)

=======
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
>>>>>>> upstream/main
