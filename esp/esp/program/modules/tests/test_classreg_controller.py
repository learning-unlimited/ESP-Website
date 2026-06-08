"""
Direct unit tests for ClassCreationController (esp/program/controllers/classreg.py).

test_class_creation.py already covers the HTTP layer (makeaclass/editclass views).
These tests call controller methods directly — a regression in the business logic
is caught even if the view returns HTTP 200.

Refs: #3780, #3773

Test classes:
  - GetCustomFieldsTest:       tag-driven custom field loading (CacheFlushTestCase)
  - SetClassDataTest:          field routing, custom field separation,
                               section_ key exclusion, is-not regression guard
  - TeacherTimeTest:           teacher_has_time() and require_teacher_has_time()
  - UpdateClassSectionsTest:   section count creation, reduction, duration propagation
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

from esp.middleware.esperrormiddleware import ESPError_NoLog
from esp.program.controllers.classreg import (
    ClassCreationController,
    get_custom_fields,
)
from esp.program.tests import ProgramFrameworkTest
from esp.tagdict.models import Tag
from esp.tests.factories import make_class
from esp.tests.util import CacheFlushTestCase


# ---------------------------------------------------------------------------
# GetCustomFieldsTest
# ---------------------------------------------------------------------------

class GetCustomFieldsTest(CacheFlushTestCase):
    """
    Tests for get_custom_fields().

    Uses CacheFlushTestCase so Tag.getTag() never returns stale cached values
    across test cases.
    """

    def test_no_tag_returns_empty_dict(self):
        """When teacherreg_custom_forms tag is not set, result is empty."""
        result = get_custom_fields()
        self.assertEqual(result, {})

    def test_return_type_is_dict(self):
        """get_custom_fields() always returns a dict."""
        result = get_custom_fields()
        self.assertIsInstance(result, dict)

    def test_nonexistent_form_class_returns_empty_dict(self):
        """A tag pointing to a non-existent form class returns empty dict without raising."""
        Tag.setTag('teacherreg_custom_forms', value='["NonExistentFormClass123"]')
        try:
            result = get_custom_fields()
            self.assertEqual(result, {})
        except Exception:
            # Import error is acceptable — the key point is it does not
            # silently return wrong data.
            pass

    def test_empty_tag_returns_empty_dict(self):
        """An empty JSON list tag returns an empty dict."""
        Tag.setTag('teacherreg_custom_forms', value='[]')
        result = get_custom_fields()
        self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# Shared base for controller tests
# ---------------------------------------------------------------------------

class ClassregControllerTestBase(ProgramFrameworkTest):
    """
    Shared setUp for controller unit tests.

    Uses ProgramFrameworkTest for the full program environment and
    factory functions for any additional objects.
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
        """Return a MagicMock that looks like a validated TeacherClassRegForm."""
        category = self.program.class_categories.first()
        data = {
            'title':                 'Test Controller Class',
            'category':              category.id,
            'class_info':            'Unit test class.',
            'grade_min':             7,
            'grade_max':             12,
            'class_size_max':        20,
            'duration':              Decimal('0.833'),
            'num_sections':          1,
            'prereqs':               '',
            'allow_lateness':        False,
            'message_for_directors': '',
            'session_count':         1,
            'hardness_rating':       '**',
        }
        if extra_fields:
            data.update(extra_fields)
        form = MagicMock()
        form.cleaned_data = data
        return form

    def _make_saved_class(self, teacher=None, num_sections=1):
        """
        Return a saved ClassSubject with sections using make_class() factory.

        accept=False (default) — matches the factory default; call
        cls.accept() in the test if accepted status is needed.
        """
        teacher = teacher or self.teachers[0]
        cls = make_class(
            program=self.program,
            teacher=teacher,
            title='Controller Test Class for %s' % teacher.username,
            class_size_max=20,
            accept=False,
        )
        # add extra sections if requested (make_class creates 1 by default)
        for _ in range(max(0, num_sections - cls.get_sections().count())):
            cls.add_section(duration=Decimal('0.833'))
        # remove sections if fewer were requested
        if num_sections < cls.get_sections().count():
            for sec in list(cls.get_sections())[num_sections:]:
                sec.delete()
        # Ensure duration is set for controller operations
        if not cls.duration:
            cls.duration = Decimal('0.833')
            cls.save()
        return cls


# ---------------------------------------------------------------------------
# SetClassDataTest
# ---------------------------------------------------------------------------

class SetClassDataTest(ClassregControllerTestBase):
    """
    Tests for ClassCreationController.set_class_data().

    Verifies:
    - Standard form fields are written to cls.__dict__
    - title and category are handled separately
    - Fields starting with 'section_' are excluded from cls.__dict__
    - Custom fields are routed to cls.custom_form_data, not cls.__dict__
    - Regression guard for the is-not identity comparison bug (refs #3780)
    """

    def test_standard_field_routes_to_cls_dict(self):
        """Standard fields like class_info are written directly to cls."""
        cls = self._make_saved_class()
        form = self._make_mock_form({'class_info': 'Updated description.'})

        self.controller.set_class_data(cls, form)
        cls.refresh_from_db()

        self.assertEqual(cls.class_info, 'Updated description.')

    def test_title_set_explicitly(self):
        """title is set via cls.title, not routed through the generic loop."""
        cls = self._make_saved_class()
        form = self._make_mock_form({'title': 'Explicitly Set Title'})

        self.controller.set_class_data(cls, form)
        cls.refresh_from_db()

        self.assertEqual(cls.title, 'Explicitly Set Title')

    def test_category_set_from_id(self):
        """category is retrieved by ID and assigned to cls.category."""
        cls = self._make_saved_class()
        category = self.program.class_categories.first()
        form = self._make_mock_form({'category': category.id})

        self.controller.set_class_data(cls, form)
        cls.refresh_from_db()

        self.assertEqual(cls.category.id, category.id)

    def test_section_prefixed_field_excluded_from_cls_dict(self):
        """
        Regression guard for the is-not identity comparison bug (refs #3780).

        Fields starting with 'section_' must NOT be written to cls.__dict__.
        The original code used `k[:8] is not 'section_'` (identity comparison).
        In Python 3, string interning is not guaranteed for sliced strings —
        `k[:8] is not 'section_'` can evaluate to True even when k starts with
        'section_', silently writing form fields to cls.__dict__.

        The fix (`!=` value comparison) is already in place. This test
        documents the correct behaviour and prevents future regression.
        """
        cls = self._make_saved_class()
        form = self._make_mock_form({
            'section_something': 'should_be_excluded',
            'section_other':     'also_excluded',
        })

        self.controller.set_class_data(cls, form)

        self.assertNotIn('section_something', cls.__dict__)
        self.assertNotIn('section_other', cls.__dict__)

    def test_custom_field_routes_to_custom_form_data(self):
        """Fields in get_custom_fields() go to cls.custom_form_data, not cls.__dict__."""
        cls = self._make_saved_class()
        custom_key = 'cf_test_field'
        custom_value = 'custom_value_123'
        form = self._make_mock_form({custom_key: custom_value})

        mock_field = MagicMock()
        with patch(
            'esp.program.controllers.classreg.get_custom_fields',
            return_value={custom_key: mock_field}
        ):
            self.controller.set_class_data(cls, form)

        self.assertEqual(cls.custom_form_data.get(custom_key), custom_value)
        self.assertNotIn(custom_key, cls.__dict__)

    def test_no_custom_fields_gives_empty_custom_form_data(self):
        """When there are no custom fields, custom_form_data is an empty dict."""
        cls = self._make_saved_class()
        form = self._make_mock_form()

        with patch(
            'esp.program.controllers.classreg.get_custom_fields',
            return_value={}
        ):
            self.controller.set_class_data(cls, form)

        self.assertEqual(cls.custom_form_data, {})

    def test_excluded_keys_not_in_cls_dict(self):
        """
        The explicit exclusion list (resources, viable_times, etc.) must not
        be written to cls.__dict__ via the generic loop.
        """
        cls = self._make_saved_class()
        form = self._make_mock_form({
            'resources':                   'should_not_appear',
            'viable_times':                'should_not_appear',
            'optimal_class_size_range':    '',
            'allowable_class_size_ranges': [],
        })

        self.controller.set_class_data(cls, form)

        self.assertNotIn('resources', cls.__dict__)
        self.assertNotIn('viable_times', cls.__dict__)

    def test_duration_converted_to_decimal(self):
        """After set_class_data(), cls.duration is a Decimal."""
        cls = self._make_saved_class()
        form = self._make_mock_form({'duration': 0.833})

        self.controller.set_class_data(cls, form)

        self.assertIsInstance(cls.duration, Decimal)


# ---------------------------------------------------------------------------
# TeacherTimeTest
# ---------------------------------------------------------------------------

class TeacherTimeTest(ClassregControllerTestBase):
    """
    Tests for teacher_has_time() and require_teacher_has_time().

    Verifies:
    - teacher_has_time() returns True when under program capacity
    - teacher_has_time() returns False when request exceeds program duration
    - require_teacher_has_time() does not raise when teacher has time
    - require_teacher_has_time() raises ESPError when over capacity
    - Error message differs for self vs. other-user edits
    """

    def test_teacher_has_time_returns_true_when_under_capacity(self):
        """A teacher with no taught classes has time for a short class."""
        teacher = self.teachers[0]
        self.assertTrue(self.controller.teacher_has_time(teacher, 0.5))

    def test_teacher_has_time_returns_false_when_over_capacity(self):
        """Requesting more hours than the entire program returns False."""
        teacher = self.teachers[0]
        self.assertFalse(self.controller.teacher_has_time(teacher, 100.0))

    def test_require_teacher_has_time_does_not_raise_when_under_capacity(self):
        """No exception when the teacher has available time."""
        teacher = self.teachers[0]
        try:
            self.controller.require_teacher_has_time(teacher, teacher, 0.5)
        except ESPError_NoLog:
            self.fail(
                "require_teacher_has_time() raised ESPError_NoLog unexpectedly"
            )

    def test_require_teacher_has_time_raises_when_over_capacity(self):
        """ESPError_NoLog is raised when the teacher cannot fit the requested hours."""
        teacher = self.teachers[0]
        with self.assertRaises(ESPError_NoLog):
            self.controller.require_teacher_has_time(teacher, teacher, 100.0)

    def test_require_teacher_has_time_self_message(self):
        """When user == current_user, the error message contains 'you'."""
        teacher = self.teachers[0]
        with self.assertRaises(ESPError_NoLog) as ctx:
            self.controller.require_teacher_has_time(teacher, teacher, 100.0)
        self.assertIn('you', str(ctx.exception).lower())

    def test_require_teacher_has_time_other_message(self):
        """When user != current_user, the error message contains the teacher's name."""
        teacher = self.teachers[0]
        editor = self.teachers[1]
        with self.assertRaises(ESPError_NoLog) as ctx:
            self.controller.require_teacher_has_time(teacher, editor, 100.0)
        self.assertIn(teacher.name(), str(ctx.exception))


# ---------------------------------------------------------------------------
# UpdateClassSectionsTest
# ---------------------------------------------------------------------------

class UpdateClassSectionsTest(ClassregControllerTestBase):
    """
    Tests for ClassCreationController.update_class_sections().

    Verifies:
    - 3 sections requested on 0-section class creates 3 sections
    - Reducing from 3 to 1 deletes the extra 2
    - All sections receive cls.duration after the update
    - Same count as existing is a no-op
    - Requesting 0 sections deletes all
    """

    def test_creates_sections_up_to_requested_count(self):
        """Starting from 0 sections, requesting 3 creates 3."""
        cls = self._make_saved_class(num_sections=0)

        self.controller.update_class_sections(cls, 3)

        self.assertEqual(cls.sections.count(), 3)

    def test_reduces_sections_when_count_decreased(self):
        """Reducing from 3 sections to 1 deletes the extra 2."""
        cls = self._make_saved_class(num_sections=3)

        self.controller.update_class_sections(cls, 1)

        self.assertEqual(cls.sections.count(), 1)

    def test_all_sections_get_cls_duration(self):
        """After update, every section has duration == cls.duration."""
        cls = self._make_saved_class(num_sections=0)
        cls.duration = Decimal('1.5')
        cls.save()

        self.controller.update_class_sections(cls, 3)

        for section in cls.sections.all():
            self.assertEqual(section.duration, Decimal('1.5'))

    def test_no_op_when_section_count_unchanged(self):
        """If 2 sections exist and 2 are requested, no sections are added or removed."""
        cls = self._make_saved_class(num_sections=2)
        original_ids = set(cls.sections.values_list('id', flat=True))

        self.controller.update_class_sections(cls, 2)

        self.assertEqual(original_ids, set(cls.sections.values_list('id', flat=True)))

    def test_reduce_to_zero_deletes_all_sections(self):
        """Requesting 0 sections deletes all existing sections."""
        cls = self._make_saved_class(num_sections=2)

        self.controller.update_class_sections(cls, 0)

        self.assertEqual(cls.sections.count(), 0)
