import unittest
from unittest.mock import MagicMock

from esp.program.controllers.autoscheduler import constraints, testutils


class CompositeConstraintCheckSwapSectionsTest(unittest.TestCase):
    """Tests for CompositeConstraint.check_swap_sections."""

    def setUp(self):
        """Create a schedule with two assigned sections for swap tests."""
        self.schedule = testutils.create_test_schedule_2()
        self.section1 = self.schedule.class_sections[1]
        self.section2 = self.schedule.class_sections[2]
        classroom = self.schedule.classrooms["26-100"]
        self.section1.assign_roomslots([classroom.availability[4]])

    def _make_composite(self, child_constraints):
        composite = constraints.CompositeConstraint.__new__(
            constraints.CompositeConstraint)
        composite.constraints = child_constraints
        return composite

    def test_delegates_to_plural_check_swap_sections(self):
        """Delegates to each child's check_swap_sections method."""
        mock_c = MagicMock()
        mock_c.check_swap_sections.return_value = None
        composite = self._make_composite([mock_c])

        result = composite.check_swap_sections(
            self.section1, self.section2, self.schedule)

        mock_c.check_swap_sections.assert_called_once_with(
            self.section1, self.section2, self.schedule)
        self.assertIsNone(result)

    def test_returns_first_violation(self):
        """Returns the first violation emitted by child constraints."""
        violation = constraints.ConstraintViolation("FakeConstraint", "reason")
        mock_ok = MagicMock()
        mock_ok.check_swap_sections.return_value = None
        mock_bad = MagicMock()
        mock_bad.check_swap_sections.return_value = violation

        composite = self._make_composite([mock_ok, mock_bad])
        result = composite.check_swap_sections(
            self.section1, self.section2, self.schedule)

        self.assertIs(result, violation)

    def test_returns_none_when_no_violations(self):
        """Returns None when all child constraints pass."""
        composite = self._make_composite([
            constraints.ContiguousConstraint(),
        ])
        result = composite.check_swap_sections(
            self.section1, self.section2, self.schedule)
        self.assertIsNone(result)

    def test_teacher_availability_violation_detected(self):
        """Detects a real availability violation during a swap check."""
        composite = self._make_composite([
            constraints.TeacherAvailabilityConstraint(),
        ])
        result = composite.check_swap_sections(
            self.section1, self.section2, self.schedule)
        self.assertIsInstance(result, constraints.ConstraintViolation)


if __name__ == "__main__":
    unittest.main()
