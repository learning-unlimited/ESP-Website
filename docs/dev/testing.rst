Testing Guide
=============

This document explains how to write tests for the ESP Website codebase, with a focus on program module handlers and behavioral invariants.

Running Tests
-------------

``contributing.rst`` covers the test-running workflow in full: the Docker
invocation, database reuse, and parallel runs. This section only shows how to
narrow a run down to the tests you care about while writing them.

Test settings come from ``esp/pytest.ini``, so no ``--settings`` flag is needed.
All paths below are relative to the ``esp`` directory.

To run a specific test file::

  pytest esp/program/modules/tests/test_class_creation.py

To run a specific test class::

  pytest esp/program/modules/tests/test_class_creation.py::MakeAClassViewTest

To run a single test method::

  pytest esp/program/modules/tests/test_class_creation.py::MakeAClassViewTest::test_makeaclass_post_valid_creates_class

Test Framework Overview
------------------------

ESP tests use pytest with the pytest-django plugin, on top of ESP-specific
infrastructure:

- **ProgramFrameworkTest** (``esp/program/tests.py``): Base class that creates a complete program with students, teachers, admins, classes, and timeslots in setUp()
- **ModuleHandlerTestMixin** (``esp/program/modules/tests/support/mixins.py``): Shared helpers for testing module handlers (login, URL building, assertions)
- **Factories** (``esp/tests/factories.py``): ``make_user()``, ``make_program()``, and ``make_class()`` build single objects directly, for tests that do not need a whole program

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
- ``assert_view_ok(url)`` — Assert GET returns HTTP 200, and return the response
- ``assert_view_forbidden(url)`` — Assert GET returns HTTP 302 or 403
- ``post_to_module(tl, view, data)`` — POST data to a handler
- ``get_module_obj(handler_name)`` — Get ProgramModuleObj for direct method calls

**Example**: Access control test::

  def test_admin_can_access(self):
      self.login_as('admin')
      url = self.get_module_url('manage', 'finaidapprove')
      self.assert_view_ok(url)

  def test_student_cannot_access(self):
      self.login_as('student')
      url = self.get_module_url('manage', 'finaidapprove')
      response = self.client.get(url)
      self.assertEqual(response.status_code, 200)
      self.assertTemplateUsed(response, 'errors/program/notanadmin.html')

Note the asymmetry: ESP's ``@needs_admin`` does not return 403 or redirect. It
renders ``errors/program/notanadmin.html`` with HTTP 200
(``esp/program/modules/base.py``), so assert on the template rather than the
status code. ``assert_view_forbidden()`` is only appropriate for views that
genuinely redirect or return 403.

**Example**: POST behavior test. Use the field names the handler actually
reads -- for ``finaidapprove`` that is a ``user`` list plus the approval
options::

  from esp.accounting.models import FinancialAidGrant
  from esp.program.models import FinancialAidRequest

  class FinAidApproveTest(ModuleHandlerTestMixin, ProgramFrameworkTest):
      def setUp(self):
          super().setUp()
          self.student = self.students[0]
          self.request = FinancialAidRequest.objects.create(
              program=self.program,
              user=self.student,
              household_income='30000',
              extra_explaination='Need help.',
          )

      def test_post_creates_financial_aid_grant(self):
          self.login_as('admin')
          response = self.post_to_module('manage', 'finaidapprove', {
              'user': [str(self.student.id)],
              'approve_blanks': 'on',
              'amount_max_dec': '25.00',
              'percent': '100',
          })
          self.assertIn(response.status_code, [200, 302])
          self.assertTrue(
              FinancialAidGrant.objects.filter(request=self.request).exists()
          )

Writing Controller Tests
-------------------------

Controllers contain business logic. Test them by calling methods directly.

**Example**: Testing ClassCreationController::

  from decimal import Decimal

  from esp.program.controllers.classreg import ClassCreationController
  from esp.program.tests import ProgramFrameworkTest

  class UpdateClassSectionsTest(ProgramFrameworkTest):
      def setUp(self, *args, **kwargs):
          super().setUp(*args, **kwargs)
          self.add_user_profiles()
          self.controller = ClassCreationController(self.program)

      def test_creates_sections_up_to_requested_count(self):
          cls = self.program.classes()[0]
          cls.duration = Decimal('0.833')
          cls.save()

          self.controller.update_class_sections(cls, 3)

          self.assertEqual(cls.sections.count(), 3)

Two things to know before calling these methods:

- ``update_class_sections()`` creates sections with ``cls.duration``. The test
  fixtures set a duration on sections but leave ``ClassSubject.duration`` unset,
  so set it explicitly first or section creation fails.
- ``set_class_data()`` and ``make_class_happen()`` take a bound, validated
  ``TeacherClassRegForm``, not a plain dict, since they read
  ``reg_form.cleaned_data``. Build one with ``controller.get_forms(reg_data)``,
  which validates the POST data and raises ``ClassCreationValidationError`` if
  it is invalid.

``esp/program/controllers/test_classreg_controller.py`` shows both patterns,
including a ``MagicMock`` stand-in for the form.

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
          error = sec_b.cannotAdd(student, checkFull=True,
                                  autocorrect_constraints=False)
          self.assertTrue(error)
          self.assertIn('conflicts', error.lower())

``cannotAdd()`` returns an error string when the student may not join, and a
falsy value when they may. Pass ``autocorrect_constraints=False`` in tests:
with the default of ``True`` it may resolve the constraint itself and report no
error, which is not what a conflict test is trying to observe.

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

  error = section.cannotAdd(student, checkFull=True,
                            autocorrect_constraints=False)
  self.assertTrue(error)
  self.assertIn('conflicts', error.lower())

Grade filtering is enforced on the ``ClassSubject``, not the section::

  error = section.parent_class.cannotAdd(student, checkFull=True)
  self.assertTrue(error)
  self.assertIn('requested grade range', error.lower())

Test Organization
-----------------

File Structure
~~~~~~~~~~~~~~

Tests live in the application directory of the code they cover, either as a
single ``tests.py`` or as a ``tests/`` package once an app has enough of them::

  esp/program/models/class_.py  ->  esp/program/tests.py
  esp/accounting/models.py      ->  esp/accounting/tests/test_models.py

Controller tests sit next to the controller they cover::

  esp/program/controllers/classreg.py  ->  esp/program/controllers/test_classreg_controller.py
  esp/program/controllers/lottery.py   ->  esp/program/controllers/test_lottery_controller.py

Program module handler tests are the exception: they are collected together
under ``esp/program/modules/tests/``, not next to the handler::

  esp/program/modules/handlers/finaidapprovemodule.py
  esp/program/modules/tests/test_finaidapprove.py

Naming
~~~~~~

- Test files: ``test_<module_name>.py``. Some older files in
  ``esp/program/modules/tests/`` are named ``<module_name>.py`` instead, which
  matches none of the collection patterns in ``esp/pytest.ini``. Use the
  ``test_`` prefix on new files so pytest collects them directly.
- Test classes: ``<Feature>Test`` (e.g., ``EnrollmentConflictTest``). The
  patterns pytest collects are set in ``esp/pytest.ini``.
- Test methods: ``test_<what_it_tests>``

Code Coverage
-------------

CI uploads coverage to Codecov, which enforces one gate (``codecov.yml``):
overall project coverage must stay at or above 75%. It appears as the
``codecov/project`` check on the pull request.

There is no per-pull-request patch coverage gate at present, so new code is not
required to hit a coverage number to merge. Add tests anyway -- the project
floor only holds if contributions carry their own coverage.

Debugging Failed Tests
-----------------------

When a test fails:

1. **Read the assertion message**::

     AssertionError: Expected HTTP 200, got 403

2. **Add print statements**::

     print(f"User: {user}, Authenticated: {user.is_authenticated}")

3. **Check test isolation**: Does the test pass alone but fail in the suite?

4. **Rebuild the test database**: The database is reused between runs, so after
   a branch switch or a new migration, run ``pytest --create-db`` once.

Further Reading
---------------

- Django testing: https://docs.djangoproject.com/en/stable/topics/testing/
- ProgramFrameworkTest source: ``esp/program/tests.py``
- ModuleHandlerTestMixin source: ``esp/program/modules/tests/support/mixins.py``
- Factories source: ``esp/tests/factories.py``
- Example handler tests: ``esp/program/modules/tests/test_finaidapprove.py``
- Example view tests: ``esp/program/modules/tests/test_class_creation.py``

