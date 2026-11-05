"""
Regression test for concurrent payment notifications (record_payment_from_identifier).

Uses TransactionTestCase so each thread commits for real and sees the same
database semantics as production. TestCase wraps tests in a transaction that is
rolled back, which hides the row locking this test is about.
"""

import threading
import unittest
from decimal import Decimal

from django.contrib.auth.models import Group
from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from esp.accounting import DuplicatePaymentError
from esp.accounting.controllers import (
    GlobalAccountingController,
    IndividualAccountingController,
    ProgramAccountingController,
)
from esp.accounting.models import LineItemType, Transfer
from esp.program.models import Program
from esp.tests.util import user_role_setup
from esp.users.models import ESPUser


class ReconciliationConcurrencyRegressionTest(TransactionTestCase):
    """
    Two threads deliver the same payment notification at once.

    Without a row lock both can pass the duplicate-transaction check before
    either commits, bank two payments for one transaction, and double the
    student's credit. With it, one thread wins and the other is rejected.
    """

    def setUp(self):
        # SQLite ignores row locks; this regression targets backends used in production.
        if not getattr(connection.features, 'has_select_for_update', False):
            raise unittest.SkipTest(
                'Database backend must support SELECT ... FOR UPDATE (not available on SQLite).'
            )
        super().setUp()

        user_role_setup()
        Group.objects.get_or_create(name='Student')
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        self.user = ESPUser.objects.create_user(
            username='teststu', password='password',
        )
        GlobalAccountingController().setup_accounts()
        self.pac = ProgramAccountingController(self.program)
        self.pac.setup_accounts()
        self.pac.setup_lineitemtypes(50.0)
        LineItemType.objects.create(
            text='T-shirt', amount_dec=Decimal('15.00'), required=False,
            max_quantity=5, program=self.program, for_payments=False,
        )

        self.iac = IndividualAccountingController(self.program, self.user)
        self.iac.ensure_required_transfers()
        self.iac.apply_preferences([('T-shirt', 1, None, None)])
        self.identifier = self.iac.get_identifier()
        self.amount_due = self.iac.amount_due()

    def test_concurrent_notifications_for_one_transaction(self):
        # Synchronize both workers so they hit the duplicate check together,
        # maximizing contention on the locked user row.
        barrier = threading.Barrier(2, timeout=60)
        results = []
        results_lock = threading.Lock()

        def reconcile_attempt():
            """
            Each thread must use its own DB connection; close stale connections
            before ORM use in a new thread (Django docs / database reference).
            """
            close_old_connections()
            try:
                barrier.wait()
                try:
                    IndividualAccountingController.record_payment_from_identifier(
                        self.identifier, self.amount_due, transaction_id='cs-1')
                    outcome = None
                except Exception as exc:
                    outcome = exc
                with results_lock:
                    results.append(outcome)
            finally:
                close_old_connections()

        threads = [threading.Thread(target=reconcile_attempt) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        successes = [r for r in results if r is None]
        failures = [r for r in results if r is not None]
        self.assertEqual(
            len(successes), 1,
            'Expected exactly one notification to be banked; got %r' % (results,))
        self.assertIsInstance(failures[0], DuplicatePaymentError)

        payments = Transfer.objects.filter(
            user=self.user, line_item__for_payments=True, transaction_id='cs-1')
        self.assertEqual(payments.count(), 1)
        self.assertEqual(self.iac.amount_paid(), Decimal('65.00'))
        self.assertEqual(self.iac.amount_due(), Decimal('0.00'))
