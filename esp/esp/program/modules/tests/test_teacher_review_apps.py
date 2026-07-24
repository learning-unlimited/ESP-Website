__author__    = "Individual contributors (see AUTHORS file)"
__date__      = "$DATE$"
__rev__       = "$REV$"
__license__   = "AGPL v.3"
__copyright__ = """
This file is part of the ESP Web Site
Copyright (c) 2007 by the individual contributors
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

import random
from esp.program.tests import ProgramFrameworkTest
from esp.users.models import ESPUser
from esp.program.models import StudentApplication, StudentAppQuestion, StudentAppResponse

class TeacherReviewAppsTest(ProgramFrameworkTest):
    def setUp(self, *args, **kwargs):
        """Set up test fixtures with Program, ClassSubject, and Teacher"""
        super().setUp(num_students=10, *args, **kwargs)

        # Add student and teacher profiles
        self.add_student_profiles()

        # Schedule classes and register students
        self.schedule_randomly()
        self.classreg_students()

        # Select a teacher and their class
        self.teacher = random.choice(self.teachers)
        self.cls = random.choice(self.teacher.getTaughtClasses(self.program))

        # Create an unauthorized teacher
        self.unauthorized_teacher, created = ESPUser.objects.get_or_create(
            username='unauthorized_teacher',
            first_name='Unauthorized',
            last_name='Teacher',
            email='unauthorized_teacher@example.com'
        )
        self.unauthorized_teacher.set_password('password')
        self.unauthorized_teacher.save()
        self.unauthorized_teacher.makeRole('Teacher')

        # Create student applications
        # Clean up any existing applications for this program to avoid ID conflicts with --keepdb
        StudentApplication.objects.filter(program=self.program).delete()
        self.students_with_apps = []
        self.student_apps = []
        class_roster = []
        for reg_type, students in self.cls.students_dict().items():
            class_roster.extend(students)
        for student in class_roster[:2]:
            app = student.getApplication(self.program, create=True)
            self.students_with_apps.append(student)
            self.student_apps.append(app)

        # Create some student app questions
        # Clean up any existing questions for this class
        StudentAppQuestion.objects.filter(subject=self.cls).delete()
        for i in range(2):
            StudentAppQuestion.objects.create(
                subject=self.cls,
                question=f"Test Question {i+1}"
            )

        # Ensure newly created questions are attached to existing applications
        for app in self.student_apps:
            app.set_questions()

        # Make the second student's application completed
        if len(self.student_apps) > 1:
            for question in self.student_apps[1].questions.all():
                StudentAppResponse.objects.create(
                    question=question,
                    complete=True
                )

    def test_review_students_valid(self):
        """Test that a valid teacher can access the review_students view (200 OK)"""
        self.assertTrue(
            self.client.login(username=self.teacher.username, password='password'),
            "Failed to log in as teacher"
        )

        url = f"{self.program.get_teach_url()}review_students/{self.cls.id}/"
        response = self.client.get(url)
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}"
        )
        # Ensure the view returns some content so that it is actually exercised
        self.assertTrue(response.content, "Expected non-empty response content")
        # Check that the roster is rendered
        self.assertContains(response, self.cls.title)

    def test_rejection_invalid_class(self):
        """Test that a non-existent class ID returns 404 or error"""
        self.assertTrue(
            self.client.login(username=self.teacher.username, password='password'),
            "Failed to log in as teacher"
        )

        invalid_class_id = 999999
        url = f"{self.program.get_teach_url()}review_students/{invalid_class_id}/"
        response = self.client.get(url)
        # Should be error response (500) due to ESPError
        self.assertEqual(
            response.status_code,
            500,
            f"Expected 500, got {response.status_code}"
        )
        # Check that the error message is present
        self.assertContains(response, 'Cannot find class with ID', status_code=500)

    def test_rejection_unauthorized(self):
        """Test that a teacher without edit permissions is rejected"""
        self.assertTrue(
            self.client.login(username=self.unauthorized_teacher.username, password='password'),
            "Failed to log in as unauthorized teacher"
        )

        url = f"{self.program.get_teach_url()}review_students/{self.cls.id}/"

        response = self.client.get(url)
        # Should be error (500) for unauthorized teacher due to ESPError
        self.assertEqual(
            response.status_code,
            500,
            f"Expected 500 for unauthorized teacher, got {response.status_code}"
        )
        # Check that the error message is present
        self.assertContains(response, 'You cannot edit class', status_code=500)

    def test_prev_redirect(self):
        """Test the redirect logic when ?prev=ID goes to next completed application"""
        self.assertTrue(
            self.client.login(username=self.teacher.username, password='password'),
            "Failed to log in as teacher"
        )

        # Ensure we have at least two students with apps
        self.assertGreaterEqual(len(self.students_with_apps), 2, "Fixture must provide at least two students with apps for prev/next behavior")

        prev_student = self.students_with_apps[0]
        next_student = self.students_with_apps[1]

        # The second student's app is completed in setUp

        url = f"{self.program.get_teach_url()}review_students/{self.cls.id}/?prev={prev_student.id}"

        response = self.client.get(url, follow=False)

        # View should redirect to the next completed application
        self.assertEqual(
            response.status_code,
            302,
            f"Expected 302 redirect, got {response.status_code}"
        )

        location = response["Location"]
        expected_location = f"{self.program.get_teach_url()}review_student/{self.cls.id}/?student={next_student.id}"
        self.assertTrue(
            location.endswith(expected_location),
            f"Expected redirect to {expected_location}, got {location}"
        )

    def test_app_questions(self):
        """Test that the teacher's app questions view works correctly"""
        self.assertTrue(
            self.client.login(username=self.teacher.username, password='password'),
            "Failed to log in as teacher"
        )

        url = f"{self.program.get_teach_url()}app_questions/"

        response = self.client.get(url)
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}"
        )

        # Verify that the response contains form elements for questions
        self.assertContains(response, 'question', status_code=200)
