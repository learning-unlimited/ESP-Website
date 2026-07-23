Testing Guide
=============

This document explains how to write tests for the ESP Website codebase, with a focus on program module handlers and behavioral invariants.

Running Tests
-------------

To run all tests::

  python manage.py test --settings=esp.test_settings

To run a specific test file::

  python manage.py test esp.program.modules.tests.test_class_creation --settings=esp.test_settings

To run a specific test class::

  python manage.py test esp.program.modules.tests.test_class_creation.ClassCreationTestMixin --settings=esp.test_settings

To run a single test method::

  python manage.py test esp.program.modules.tests.test_class_creation.ClassCreationTestMixin.test_makeaclass_post_valid_creates_class --settings=esp.test_settings

Test Framework Overview
------------------------

ESP tests use Django's test framework with ESP-specific infrastructure:

- **ProgramFrameworkTest** (``esp/program/tests.py``): Base class that creates a complete program with students, teachers, admins, classes, and timeslots in setUp()
- **ModuleHandlerTestMixin** (``esp/program/modules/tests/support/mixins.py``): Shared helpers for testing module handlers (login, URL building, assertions)

Writing Module Handler Tests
-----------------------------

Module handler tests verify that program module views work correctly.

Basic Pattern Without Mixin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Traditional handler test pattern::

  from esp.program.tests import ProgramFrameworkTest

  class MyHandlerTest(ProgramFrameworkTest):
      def test_handler_renders(self):
          admin = self.admins[0]
          self.assertTrue(
              self.client.login(username=admin.username, password='password')
          )
          url = '/manage/%s/myview' % self.program.url
          response = self.client.get(url)
          self.assertEqual(response.status_code, 200)

Using ModuleHandlerTestMixin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ModuleHandlerTestMixin reduces boilerplate::

  from esp.program.tests import ProgramFrameworkTest
  from esp.program.modules.tests.support import ModuleHandlerTestMixin

  class MyHandlerTest(ModuleHandlerTestMixin, ProgramFrameworkTest):
      def test_handler_renders(self):
          self.login_as('admin')
          url = self.get_module_url('manage', 'myview')
          self.assert_view_ok(url)

**Available Methods:**

- ``login_as(role)`` — Log in as 'admin', 'teacher', or 'student'
- ``get_module_url(tl, view)`` — Build URLs like ``/manage/TestProgram/2222_Summer/myview``
- ``assert_view_ok(url)`` — Assert GET returns HTTP 200
- ``assert_view_forbidden(url)`` — Assert GET returns HTTP 302 or 403
- ``post_to_module(tl, view, data)`` — POST data to a handler
- ``get_module_obj(handler_name)`` — Get ProgramModuleObj for direct method calls

**Example**: Access control test::

  def test_admin_can_access(self):
      self.login_as('admin')
      url = self.get_module_url('manage', 'finaidapprove')
      self.assert_view_ok(url)

  def test_teacher_cannot_access(self):
      self.login_as('teacher')
      url = self.get_module_url('manage', 'finaidapprove')
      self.assert_view_forbidden(url)

**Example**: POST behavior test::

  def test_approve_application(self):
      self.login_as('admin')
      response = self.post_to_module('manage', 'finaidapprove', {
          'user_id': self.students[0].id,
          'approve': 'yes'
      })
      self.assertEqual(response.status_code, 200)

Writing Controller Tests
-------------------------

Controllers contain business logic. Test them by calling methods directly.

**Example**: Testing ClassCreationController::

  from esp.program.controllers.classreg import ClassCreationController
  from esp.program.tests import ProgramFrameworkTest
  from esp.program.models.class_ import ClassSubject

  class ClassCreationControllerTest(ProgramFrameworkTest):
      def test_set_class_data_basic(self):
          subject = self.program.classes()[0]
          teacher = self.teachers[0]
          controller = ClassCreationController(self.program)

          # Create form data
          form_data = {
              'title': 'New Title',
              'category': self.categories[0].id
          }

          result = controller.set_class_data(subject, form_data)
          
          subject.refresh_from_db()
          self.assertEqual(subject.title, 'New Title')

Writing Behavioral Invariant Tests
-----------------------------------

Behavioral tests verify critical system invariants hold.

**Example**: Student registration invariants::

  from esp.program.tests import ProgramFrameworkTest
  from esp.program.models import StudentRegistration

  class EnrollmentConflictTest(ProgramFrameworkTest):
      def setUp(self):
          super().setUp()
          self.add_user_profiles()
          self.schedule_randomly()

      def test_conflict_prevents_enrollment(self):
          """Students cannot enroll in overlapping classes."""
          timeslot = self.program.getTimeSlots()[0]
          sections = list(self.program.sections()[:2])
          sec_a, sec_b = sections[0], sections[1]

          # Force both sections to same timeslot
          sec_a.meeting_times.set([timeslot])
          sec_b.meeting_times.set([timeslot])

          student = self.students[0]

          # First enrollment succeeds
          result = sec_a.preregister_student(student)
          self.assertTrue(result)

          # Second enrollment blocked by conflict
          error = sec_b.cannotAdd(student, checkFull=True)
          self.assertTrue(error)
          self.assertIn('conflicts', error.lower())

Common Test Patterns
---------------------

Using ProgramFrameworkTest Data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

ProgramFrameworkTest setUp() creates::

  self.students     # List of ESPUser objects with Student role
  self.teachers     # List of ESPUser objects with Teacher role
  self.admins       # List of ESPUser objects with Administrator role
  self.program      # Program object
  self.categories   # List of ClassCategories

Access existing classes::

  # Get all classes
  classes = self.program.classes()

  # Get a single class
  subject = self.program.classes()[0]

  # Get sections
  sections = self.program.sections()
  section = self.program.sections()[0]

Helper Methods
~~~~~~~~~~~~~~

ProgramFrameworkTest provides::

  # Give users profiles (required for registration)
  self.add_user_profiles()

  # Schedule classes to random timeslots
  self.schedule_randomly()

  # Get program timeslots
  timeslots = self.program.getTimeSlots()

Asserting Database State
~~~~~~~~~~~~~~~~~~~~~~~~~

Verify operations have expected database effects::

  # Count before
  count_before = section.students(['Enrolled']).count()

  # Perform operation
  section.preregister_student(student)

  # Count after
  count_after = section.students(['Enrolled']).count()
  self.assertEqual(count_after, count_before + 1)

  # Verify registration exists
  self.assertTrue(
      StudentRegistration.valid_objects().filter(
          user=student,
          section=section
      ).exists()
  )

Testing Error Messages
~~~~~~~~~~~~~~~~~~~~~~

Verify validation produces helpful errors::

  error = section.cannotAdd(student, checkFull=True)
  self.assertTrue(error)
  self.assertIn('conflicts', error.lower())

Test Organization
-----------------

File Structure
~~~~~~~~~~~~~~

Place tests near the code they test::

  esp/program/controllers/classreg.py
  esp/program/controllers/tests/test_classreg.py

  esp/program/modules/handlers/finaidapprovemodule.py
  esp/program/modules/tests/test_finaidapprove.py

Naming
~~~~~~

- Test files: ``test_<module_name>.py``
- Test classes: ``<Feature>Test`` (e.g., ``EnrollmentConflictTest``)
- Test methods: ``test_<what_it_tests>``

Code Coverage
-------------

The repository uses Codecov with these thresholds:

- **Project coverage**: Must remain above 70%
- **Patch coverage**: New code must be at least 60% tested

Coverage reports appear in GitHub Actions PR checks.

Debugging Failed Tests
-----------------------

When a test fails:

1. **Read the assertion message**::

     AssertionError: Expected HTTP 200, got 403

2. **Add print statements**::

     print(f"User: {user}, Authenticated: {user.is_authenticated}")

3. **Check test isolation**: Does the test pass alone but fail in the suite?

4. **Verify test database**: Run ``python manage.py migrate --settings=esp.test_settings``

Further Reading
---------------

- Django testing: https://docs.djangoproject.com/en/stable/topics/testing/
- ProgramFrameworkTest source: ``esp/program/tests.py``
- ModuleHandlerTestMixin source: ``esp/program/modules/tests/support/mixins.py``
- Example tests: ``esp/program/modules/tests/test_class_creation.py``

