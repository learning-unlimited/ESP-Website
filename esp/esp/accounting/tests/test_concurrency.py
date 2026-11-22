"""
Concurrency tests for lazily created accounting rows.

Each test races two threads through the same code path, with save() slowed
down to widen the window between the existence check and the insert, so that
without serialization both threads would create a row. They use
TransactionTestCase so each thread commits on its own database connection, as
concurrent requests do in production.
"""
import threading
import time
import unittest
from unittest import mock

from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from esp.accounting.controllers import (
    GlobalAccountingController,
    IndividualAccountingController,
    ProgramAccountingController,
)
from esp.accounting.models import FinancialAidGrant, LineItemType, Transfer
from esp.program.models import FinancialAidRequest, Program
from esp.users.models import ESPUser


def slowed_save(model):
    """Patch model.save() to pause before writing."""
    original_save = model.save

    def slow_save(instance, *args, **kwargs):
        time.sleep(0.5)
        return original_save(instance, *args, **kwargs)

    return mock.patch.object(model, 'save', slow_save)


class AccountingConcurrencyTest(TransactionTestCase):

    def setUp(self):
        # SQLite ignores row locks; this regression targets backends used in production.
        if not connection.features.has_select_for_update:
            raise unittest.SkipTest(
                'Database backend must support SELECT ... FOR UPDATE (not available on SQLite).'
            )
        super().setUp()
        self.program = Program.objects.create(grade_min=7, grade_max=12)
        GlobalAccountingController().setup_accounts()
        pac = ProgramAccountingController(self.program)
        pac.setup_accounts()
        pac.setup_lineitemtypes(50.0, [('T-shirt', 15.0, 1)])
        self.student = ESPUser.objects.create(username='student')

    def race(self, target):
        """Run target() in two threads started together; return any exceptions."""
        barrier = threading.Barrier(2, timeout=60)
        errors = []
        lock = threading.Lock()

        def attempt():
            close_old_connections()
            try:
                barrier.wait()
                target()
            except Exception as e:
                with lock:
                    errors.append(e)
            finally:
                close_old_connections()

        threads = [threading.Thread(target=attempt) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return errors

    def test_line_item_type_created_once(self):
        with slowed_save(LineItemType):
            errors = self.race(lambda: LineItemType.get_or_create_for_program(self.program, text='Donation'))
        self.assertEqual(errors, [])
        self.assertEqual(LineItemType.objects.filter(program=self.program, text='Donation').count(), 1)

    def test_admission_charged_once(self):
        def view_amount_due():
            IndividualAccountingController(self.program, self.student).ensure_required_transfers()

        with slowed_save(Transfer):
            errors = self.race(view_amount_due)
        self.assertEqual(errors, [])
        self.assertEqual(Transfer.objects.filter(
            user=self.student, line_item__text='Program admission').count(), 1)

    def test_double_submitted_preference_kept_once(self):
        def choose_tshirt():
            IndividualAccountingController(self.program, self.student).set_preference('T-shirt', 1)

        with slowed_save(Transfer):
            errors = self.race(choose_tshirt)
        self.assertEqual(errors, [])
        self.assertEqual(Transfer.objects.filter(user=self.student, line_item__text='T-shirt').count(), 1)

    def test_financial_aid_granted_once(self):
        request = FinancialAidRequest.objects.create(user=self.student, program=self.program)
        grant = FinancialAidGrant.objects.create(request=request, percent=100)

        def finalize():
            FinancialAidGrant.objects.get(pk=grant.pk).finalize()

        with slowed_save(Transfer):
            errors = self.race(finalize)
        self.assertEqual(errors, [])
        self.assertEqual(Transfer.objects.filter(
            user=self.student, line_item__text='Financial aid grant').count(), 1)
        self.assertTrue(FinancialAidGrant.objects.get(pk=grant.pk).finalized)
