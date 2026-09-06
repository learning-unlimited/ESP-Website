"""
Regression tests for the last-resort guards on student enrollment integrity.

Complements test_addclass_concurrency.py, which drives two threads through the
ajax_addclass view. These tests cover the two pieces that sit underneath it:
the unique_active_enrollment database constraint, and preregister_student()'s
ability to take its row lock when no request transaction is already open.

Refs: #5030
"""

import unittest

from django.db import IntegrityError, connection, transaction
from django.test import TransactionTestCase

from esp.program.models import RegistrationType, StudentRegistration
from esp.program.tests import ProgramFrameworkTest


class DuplicateActiveEnrollmentConstraintTest(ProgramFrameworkTest):
    """The database rejects a second live registration for the same tuple."""

    def setUp(self):
        super().setUp(num_students=1, num_teachers=1, classes_per_teacher=1,
                      sections_per_class=1)
        self.section = self.program.sections()[0]
        self.student = self.students[0]
        self.enrolled = RegistrationType.get_cached(name='Enrolled', category='student')

    def _register(self):
        return StudentRegistration.objects.create(
            user=self.student, section=self.section, relationship=self.enrolled
        )

    def test_duplicate_active_registration_is_rejected(self):
        self._register()
        # The failed INSERT poisons the surrounding transaction, so give it its
        # own savepoint to keep the test case usable afterwards.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._register()

    def test_registration_allowed_once_the_previous_one_expires(self):
        first = self._register()
        first.expire()

        second = self._register()
        self.assertNotEqual(first.pk, second.pk)
        self.assertEqual(
            StudentRegistration.valid_objects().filter(
                user=self.student, section=self.section, relationship=self.enrolled
            ).count(),
            1,
            'Only the re-registration should be live after the first one expired',
        )

    def test_different_relationships_are_independent(self):
        self._register()
        interested = RegistrationType.get_cached(name='Interested', category='student')

        StudentRegistration.objects.create(
            user=self.student, section=self.section, relationship=interested
        )
        self.assertEqual(
            StudentRegistration.valid_objects().filter(
                user=self.student, section=self.section
            ).count(),
            2,
            'The constraint is per relationship type, not per (user, section)',
        )


class PreregisterOutsideRequestTest(TransactionTestCase):
    """
    preregister_student() locks the section row, and a row lock is only legal
    inside a transaction. Requests get one from ATOMIC_REQUESTS, but the lottery
    and class-change scripts do not, so the method has to open its own.

    TransactionTestCase is what makes this meaningful: django.test.TestCase
    would wrap the test in a transaction and hide the bug.
    """

    def setUp(self):
        # SQLite ignores row locks; this regression targets production backends.
        if not getattr(connection.features, 'supports_select_for_update', False):
            raise unittest.SkipTest(
                'Database backend must support SELECT ... FOR UPDATE (not available on SQLite).'
            )
        super().setUp()

        pf = ProgramFrameworkTest()
        pf.setUp(num_students=1, num_teachers=1, classes_per_teacher=1,
                 sections_per_class=1)
        pf.add_user_profiles()
        pf.schedule_randomly()

        self.program = pf.program
        self.student = pf.students[0]
        self.section = self.program.sections().filter(meeting_times__isnull=False).first()
        self.assertIsNotNone(self.section, 'Test requires at least one scheduled section')

    def test_preregister_without_an_ambient_transaction(self):
        self.assertFalse(
            connection.in_atomic_block,
            'This test is only meaningful with no transaction already open',
        )

        self.assertTrue(
            self.section.preregister_student(self.student, prereg_verb='Enrolled'),
            'preregister_student() should succeed when called outside a request',
        )
        self.assertEqual(
            StudentRegistration.valid_objects().filter(
                user=self.student, section=self.section, relationship__name='Enrolled'
            ).count(),
            1,
        )

    def test_repeat_preregistration_does_not_duplicate(self):
        self.section.preregister_student(self.student, prereg_verb='Enrolled')
        self.section.preregister_student(self.student, prereg_verb='Enrolled')

        self.assertEqual(
            StudentRegistration.valid_objects().filter(
                user=self.student, section=self.section, relationship__name='Enrolled'
            ).count(),
            1,
            'A repeated registration should be a no-op, not a second live row',
        )
