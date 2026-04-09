from django.test import TestCase
from esp.program.models import ScheduleConstraint

class TestScheduleConstraint(TestCase):

    def test_handle_failure_noop(self):
        constraint = ScheduleConstraint(on_failure='noop')
        result = constraint.handle_failure()
        self.assertEqual(result, (None, None))

    def test_handle_failure_retry(self):
        constraint = ScheduleConstraint(on_failure='retry')
        # Mock schedule_map
        constraint.schedule_map = {'test': 'data'}
        result = constraint.handle_failure()
        self.assertIs(result, constraint.schedule_map)

    def test_handle_failure_clear(self):
        constraint = ScheduleConstraint(on_failure='clear')
        constraint.schedule_map = {'test': 'data'}
        result = constraint.handle_failure()
        self.assertIs(result, constraint.schedule_map)
        # Assuming clear is called, but since it's a dict, check if cleared
        self.assertEqual(constraint.schedule_map, {})

    def test_handle_failure_invalid(self):
        constraint = ScheduleConstraint(on_failure='malicious_code')
        result = constraint.handle_failure()
        self.assertEqual(result, (None, None))

    def test_no_exec_used(self):
        # Optional: ensure exec is not in the method's code
        self.assertNotIn('exec', ScheduleConstraint.handle_failure.__code__.co_names)