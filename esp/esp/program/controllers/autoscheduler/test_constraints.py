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

    def test_stops_after_first_violation(self):
        """Stops evaluating child constraints after the first violation."""
        violation = constraints.ConstraintViolation("FakeConstraint", "reason")
        mock_bad = MagicMock()
        mock_bad.check_swap_sections.return_value = violation
        mock_after = MagicMock()

        composite = self._make_composite([mock_bad, mock_after])
        result = composite.check_swap_sections(
            self.section1, self.section2, self.schedule)

        self.assertIs(result, violation)
        mock_bad.check_swap_sections.assert_called_once_with(
            self.section1, self.section2, self.schedule)
        mock_after.check_swap_sections.assert_not_called()

    def test_returns_none_when_no_violations(self):
        """Returns None when all child constraints pass."""
        composite = self._make_composite([
            constraints.ContiguousConstraint(),
        ])
        result = composite.check_swap_sections(
            self.section1, self.section2, self.schedule)
        self.assertIsNone(result)

    def test_precondition_violation_for_mismatched_swap_lengths(self):
        """PreconditionConstraint rejects swaps with mismatched slot counts."""
        composite = self._make_composite([
            constraints.PreconditionConstraint(),
        ])
        result = composite.check_swap_sections(
            self.section1, self.section2, self.schedule)

        self.assertIsInstance(result, constraints.ConstraintViolation)
        self.assertEqual(result.constraint_name, "PreconditionConstraint")
        self.assertIn("same number of roomslots", result.reason)

    def test_teacher_availability_violation_detected(self):
        """Detects an availability violation for an otherwise valid swap."""
        classroom = self.schedule.classrooms["26-100"]
        self.section1.clear_roomslots()
        self.section1.assign_roomslots(classroom.availability[4:6])
        self.section1.duration = self.section2.duration

        precondition = constraints.PreconditionConstraint()
        self.assertIsNone(precondition.check_swap_sections(
            self.section1, self.section2, self.schedule))

        composite = self._make_composite([
            constraints.TeacherAvailabilityConstraint(),
        ])
        result = composite.check_swap_sections(
            self.section1, self.section2, self.schedule)
        self.assertIsInstance(result, constraints.ConstraintViolation)
        self.assertEqual(
            result.constraint_name,
            "TeacherAvailabilityConstraint")
        self.assertIn("won't be available", result.reason)


if __name__ == "__main__":
    unittest.main()
