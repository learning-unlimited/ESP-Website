"""
Direct unit tests for ClassCreationController (esp/program/controllers/classreg.py).

test_class_creation.py already covers the HTTP layer (makeaclass/editclass views).
These tests call controller methods directly — a regression in the business logic
is caught even if the view returns HTTP 200.

Test families:
  - SetClassDataTest:          field routing, custom field separation,
                               section_ key exclusion, is-not regression guard
  - TeacherTimeTest:           teacher_has_time() and require_teacher_has_time()
                               capacity enforcement
  - UpdateClassSectionsTest:   section count creation, reduction, and duration
                               propagation via update_class_sections()
  - AttachAndAssociateTest:    attach_class_to_program() and
                               associate_teacher_with_class() helpers
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from esp.middleware import ESPError
from esp.program.controllers.classreg import ClassCreationController
from esp.program.models import ClassSubject
from esp.program.tests import ProgramFrameworkTest


# ---------------------------------------------------------------------------
# Shared base
# ---------------------------------------------------------------------------

class ClassregControllerTestBase(ProgramFrameworkTest):
    """
    Shared setUp for all ClassCreationController unit tests.

    Inherits a full program environment from ProgramFrameworkTest and adds
    teacher profiles (needed for getTaughtTime queries) and a controller
    instance.
    """

    def setUp(self, *args, **kwargs):
        kwargs.setdefault('num_teachers', 3)
        kwargs.setdefault('classes_per_teacher', 1)
        kwargs.setdefault('num_students', 2)
        kwargs.setdefault('num_timeslots', 3)
        kwargs.setdefault('timeslot_length', 50)
        super().setUp(*args, **kwargs)
        self.add_user_profiles()
        self.controller = ClassCreationController(self.program)

    def _make_mock_form(self, extra_fields=None):
        """
        Return a MagicMock that looks like a validated TeacherClassRegForm.

        Provides the minimal cleaned_data that set_class_data() requires:
          - title, category, class_info, grade_min, grade_max, class_size_max,
            duration, num_sections
        Pass extra_fields to add or override specific keys.
        """
        category = self.program.class_categories.first()
        data = {
            'title':          'Test Controller Class',
            'category':       category.id,
            'class_info':     'Unit test class.',
            'grade_min':      7,
            'grade_max':      12,
            'class_size_max': 20,
            'duration':       Decimal('0.833'),  # 50 minutes / 60
            'num_sections':   1,
            'prereqs':        '',
            'allow_lateness': False,
            'message_for_directors': '',
            'session_count':  1,
            'hardness_rating': '**',
        }
        if extra_fields:
            data.update(extra_fields)
        form = MagicMock()
        form.cleaned_data = data
        return form

    def _make_saved_class(self, teacher=None, num_sections=1):
        """Return a saved ClassSubject with sections, optionally with a teacher."""
        category = self.program.class_categories.first()
        cls = ClassSubject.objects.create(
            parent_program=self.program,
            category=category,
            title='Saved Test Class',
            grade_min=7,
            grade_max=12,
            class_size_max=20,
            duration=Decimal('0.833'),
            class_info='Saved for controller tests.',
        )
        if teacher:
            cls.makeTeacher(teacher)
        for _ in range(num_sections):
            cls.add_section(duration=cls.duration)
        return cls


# ---------------------------------------------------------------------------
# 1. SetClassDataTest
# ---------------------------------------------------------------------------

class SetClassDataTest(ClassregControllerTestBase):
    """
    Tests for ClassCreationController.set_class_data().

    Verifies:
    - Standard form fields are written to cls.__dict__
    - 'category' and 'title' are handled separately (not via __dict__)
    - Fields starting with 'section_' are excluded from cls.__dict__
    - Custom fields are routed to cls.custom_form_data
    - Regression guard: != operator correctly excludes section_ keys
      (guards against any future reintroduction of the is-not identity bug)
    """

    def test_standard_field_routes_to_cls_dict(self):
        """Standard fields like class_info are written directly to cls.__dict__."""
        cls = self._make_saved_class()
        form = self._make_mock_form({'class_info': 'Updated description.'})

        self.controller.set_class_data(cls, form)
        cls.refresh_from_db()

        self.assertEqual(cls.class_info, 'Updated description.',
                         "class_info should be updated on the class object")

    def test_title_set_explicitly(self):
        """title is set via cls.title, not routed through the generic loop."""
        cls = self._make_saved_class()
        form = self._make_mock_form({'title': 'Explicitly Set Title'})

        self.controller.set_class_data(cls, form)
        cls.refresh_from_db()

        self.assertEqual(cls.title, 'Explicitly Set Title',
                         "Title should be explicitly set on the class")

    def test_category_set_from_id(self):
        """category is retrieved by ID and assigned to cls.category."""
        cls = self._make_saved_class()
        category = self.program.class_categories.first()
        form = self._make_mock_form({'category': category.id})

        self.controller.set_class_data(cls, form)
        cls.refresh_from_db()

        self.assertEqual(cls.category.id, category.id,
                         "Category should be set from the cleaned_data category ID")

    def test_section_prefixed_field_excluded_from_cls_dict(self):
        """
        Fields starting with 'section_' must NOT be written to cls.__dict__.

        This is the regression guard for the is-not identity comparison bug
        described in the GSoC proposal. The current code uses != (value
        comparison) which is correct. This test will catch any future
        reintroduction of identity comparison (is not) that would
        silently misroute these fields.
        """
        cls = self._make_saved_class()
        form = self._make_mock_form({
            'section_something': 'should_be_excluded',
            'section_other':     'also_excluded',
        })

        self.controller.set_class_data(cls, form)

        # Neither section_ field should appear on cls.__dict__ after the call
        self.assertNotIn('section_something', cls.__dict__,
                         "section_something must not be written to cls.__dict__")
        self.assertNotIn('section_other', cls.__dict__,
                         "section_other must not be written to cls.__dict__")

    def test_custom_field_routes_to_custom_form_data(self):
        """
        Fields listed in get_custom_fields() are routed to cls.custom_form_data,
        not to cls.__dict__.
        """
        cls = self._make_saved_class()
        custom_key = 'cf_test_field'
        custom_value = 'custom_value_123'
        form = self._make_mock_form({custom_key: custom_value})

        # Patch get_custom_fields to return our test field
        mock_field = MagicMock()
        with patch(
            'esp.program.controllers.classreg.get_custom_fields',
            return_value={custom_key: mock_field}
        ):
            self.controller.set_class_data(cls, form)

        self.assertEqual(
            cls.custom_form_data.get(custom_key), custom_value,
            "Custom field should be routed to custom_form_data"
        )
        self.assertNotIn(
            custom_key, cls.__dict__,
            "Custom field must not appear in cls.__dict__"
        )

    def test_no_custom_fields_gives_empty_custom_form_data(self):
        """When there are no custom fields, custom_form_data is an empty dict."""
        cls = self._make_saved_class()
        form = self._make_mock_form()

        with patch(
            'esp.program.controllers.classreg.get_custom_fields',
            return_value={}
        ):
            self.controller.set_class_data(cls, form)

        self.assertEqual(cls.custom_form_data, {},
                         "custom_form_data should be empty when no custom fields exist")

    def test_duration_converted_to_decimal(self):
        """After set_class_data(), cls.duration is a Decimal, not a float."""
        cls = self._make_saved_class()
        form = self._make_mock_form({'duration': 0.833})

        self.controller.set_class_data(cls, form)

        self.assertIsInstance(
            cls.duration, Decimal,
            "cls.duration should be a Decimal after set_class_data()"
        )

    def test_excluded_fields_not_in_cls_dict(self):
        """
        The explicitly excluded fields (category, resources, viable_times,
        optimal_class_size_range, allowable_class_size_ranges, title) must
        not be written to cls.__dict__ via the generic loop.
        """
        cls = self._make_saved_class()
        form = self._make_mock_form({
            'resources':                  'should_not_appear',
            'viable_times':               'should_not_appear',
            'optimal_class_size_range':   '',
            'allowable_class_size_ranges': [],
        })

        self.controller.set_class_data(cls, form)

        self.assertNotIn('resources', cls.__dict__,
                         "'resources' must be excluded from cls.__dict__")
        self.assertNotIn('viable_times', cls.__dict__,
                         "'viable_times' must be excluded from cls.__dict__")


# ---------------------------------------------------------------------------
# 2. TeacherTimeTest
# ---------------------------------------------------------------------------

class TeacherTimeTest(ClassregControllerTestBase):
    """
    Tests for teacher_has_time() and require_teacher_has_time().

    Verifies:
    - teacher_has_time() returns True when teacher is under program capacity
    - teacher_has_time() returns False when teacher would exceed capacity
    - require_teacher_has_time() does not raise when teacher has time
    - require_teacher_has_time() raises ESPError when teacher is over capacity
    - ESPError message differs when user == current_user vs. different users
    """

    def test_teacher_has_time_returns_true_when_under_capacity(self):
        """A teacher with no taught classes should have time for a short class."""
        teacher = self.teachers[0]
        # 0.5 hours is well under the program's total duration (3 x 50min = 2.5hr)
        self.assertTrue(
            self.controller.teacher_has_time(teacher, 0.5),
            "teacher_has_time() should return True when teacher has capacity"
        )

    def test_teacher_has_time_returns_false_when_over_capacity(self):
        """Requesting more hours than the entire program should return False."""
        teacher = self.teachers[0]
        # Program has 3 timeslots of 50 minutes = 2.5 hours total.
        # Requesting 100 hours must exceed that.
        self.assertFalse(
            self.controller.teacher_has_time(teacher, 100.0),
            "teacher_has_time() should return False when request exceeds program duration"
        )

    def test_require_teacher_has_time_does_not_raise_when_under_capacity(self):
        """No exception should be raised when the teacher has available time."""
        teacher = self.teachers[0]
        try:
            self.controller.require_teacher_has_time(teacher, teacher, 0.5)
        except ESPError:
            self.fail(
                "require_teacher_has_time() raised ESPError unexpectedly "
                "when teacher had sufficient time"
            )

    def test_require_teacher_has_time_raises_when_over_capacity(self):
        """ESPError must be raised when the teacher cannot fit the requested hours."""
        teacher = self.teachers[0]
        with self.assertRaises(ESPError,
                               msg="require_teacher_has_time() should raise ESPError "
                                   "when teacher exceeds capacity"):
            self.controller.require_teacher_has_time(teacher, teacher, 100.0)

    def test_require_teacher_has_time_self_message(self):
        """When user == current_user, the ESPError message uses 'you'."""
        teacher = self.teachers[0]
        with self.assertRaises(ESPError) as ctx:
            self.controller.require_teacher_has_time(teacher, teacher, 100.0)
        # The self-message contains "you" (see classreg.py: "We love you too!")
        self.assertIn('you', str(ctx.exception).lower(),
                      "Self-referential error message should contain 'you'")

    def test_require_teacher_has_time_other_message(self):
        """When user != current_user, the ESPError mentions the teacher's name."""
        teacher = self.teachers[0]
        editor = self.teachers[1]
        with self.assertRaises(ESPError) as ctx:
            self.controller.require_teacher_has_time(teacher, editor, 100.0)
        # The other-user message contains the teacher's name
        self.assertIn(
            teacher.name(), str(ctx.exception),
            "Error message for another user should contain the teacher's name"
        )


# ---------------------------------------------------------------------------
# 3. UpdateClassSectionsTest
# ---------------------------------------------------------------------------

class UpdateClassSectionsTest(ClassregControllerTestBase):
    """
    Tests for ClassCreationController.update_class_sections().

    Verifies:
    - Requesting 3 sections on a 0-section class creates 3 sections
    - Reducing from 3 sections to 1 deletes the excess 2
    - All sections receive cls.duration after the update
    - Requesting the same number of sections as already exist is a no-op
    """

    def test_creates_sections_up_to_requested_count(self):
        """Starting from 0 sections, requesting 3 should create 3."""
        cls = self._make_saved_class(num_sections=0)
        cls.duration = Decimal('0.833')
        cls.save()

        self.controller.update_class_sections(cls, 3)

        self.assertEqual(
            cls.sections.count(), 3,
            "update_class_sections(cls, 3) should result in exactly 3 sections"
        )

    def test_reduces_sections_when_count_decreased(self):
        """Reducing from 3 sections to 1 should delete the extra 2."""
        cls = self._make_saved_class(num_sections=3)

        self.controller.update_class_sections(cls, 1)

        self.assertEqual(
            cls.sections.count(), 1,
            "update_class_sections(cls, 1) should reduce section count to 1"
        )

    def test_all_sections_get_cls_duration(self):
        """After update, every section should have duration == cls.duration."""
        cls = self._make_saved_class(num_sections=0)
        cls.duration = Decimal('1.5')
        cls.save()

        self.controller.update_class_sections(cls, 3)

        for section in cls.sections.all():
            self.assertEqual(
                section.duration, Decimal('1.5'),
                "Each section should have cls.duration after update_class_sections()"
            )

    def test_no_op_when_section_count_unchanged(self):
        """If 2 sections exist and 2 are requested, nothing is deleted or added."""
        cls = self._make_saved_class(num_sections=2)
        original_ids = set(cls.sections.values_list('id', flat=True))

        self.controller.update_class_sections(cls, 2)

        new_ids = set(cls.sections.values_list('id', flat=True))
        self.assertEqual(
            original_ids, new_ids,
            "Section IDs should not change when requested count equals existing count"
        )

    def test_reduce_to_zero_deletes_all_sections(self):
        """Requesting 0 sections should delete all existing sections."""
        cls = self._make_saved_class(num_sections=2)

        self.controller.update_class_sections(cls, 0)

        self.assertEqual(
            cls.sections.count(), 0,
            "update_class_sections(cls, 0) should delete all sections"
        )


# ---------------------------------------------------------------------------
# 4. AttachAndAssociateTest
# ---------------------------------------------------------------------------

class AttachAndAssociateTest(ClassregControllerTestBase):
    """
    Tests for attach_class_to_program() and associate_teacher_with_class().

    Verifies:
    - attach_class_to_program() sets cls.parent_program to the controller's program
    - associate_teacher_with_class() adds the teacher to the class
    """

    def test_attach_class_sets_parent_program(self):
        """attach_class_to_program() must set cls.parent_program to the controller's program."""
        cls = ClassSubject()
        self.controller.attach_class_to_program(cls)

        self.assertEqual(
            cls.parent_program, self.program,
            "attach_class_to_program() should set cls.parent_program"
        )

    def test_associate_teacher_adds_teacher_to_class(self):
        """associate_teacher_with_class() must add the teacher to cls.get_teachers()."""
        teacher = self.teachers[0]
        cls = self._make_saved_class()

        # Patch mailman so the test doesn't require a running Mailman server
        with patch('esp.program.controllers.classreg.add_list_member'):
            self.controller.associate_teacher_with_class(cls, teacher)

        self.assertIn(
            teacher.id,
            [t.id for t in cls.get_teachers()],
            "associate_teacher_with_class() should add the teacher to the class"
        )

    def test_associate_teacher_does_not_remove_existing_teachers(self):
        """Adding a second teacher must not remove the first."""
        teacher1 = self.teachers[0]
        teacher2 = self.teachers[1]
        cls = self._make_saved_class(teacher=teacher1)

        with patch('esp.program.controllers.classreg.add_list_member'):
            self.controller.associate_teacher_with_class(cls, teacher2)

        teacher_ids = [t.id for t in cls.get_teachers()]
        self.assertIn(teacher1.id, teacher_ids,
                      "First teacher should still be on the class after adding second")
        self.assertIn(teacher2.id, teacher_ids,
                      "Second teacher should be on the class after association")
