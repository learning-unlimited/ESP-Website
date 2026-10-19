"""
Concurrency test for LineItemType.get_or_create_for_program().

Uses TransactionTestCase so each worker thread commits on its own database
connection, as concurrent requests do in production.
"""
import threading
import time
import unittest
from unittest import mock

from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from esp.accounting.models import LineItemType
from esp.program.models import Program


class GetOrCreateForProgramConcurrencyTest(TransactionTestCase):

    def setUp(self):
        # SQLite ignores row locks; this regression targets backends used in production.
        if not connection.features.has_select_for_update:
            raise unittest.SkipTest(
                'Database backend must support SELECT ... FOR UPDATE (not available on SQLite).'
            )
        super().setUp()
        self.program = Program.objects.create(grade_min=7, grade_max=12)

    def test_concurrent_callers_create_one_row(self):
        barrier = threading.Barrier(2, timeout=60)
        results = []
        errors = []
        lock = threading.Lock()
        original_save = LineItemType.save

        def slow_save(lit, *args, **kwargs):
            # Widen the window between the existence check and the insert so
            # that, without serialization, both threads would create a row.
            time.sleep(0.5)
            return original_save(lit, *args, **kwargs)

        def attempt():
            close_old_connections()
            try:
                barrier.wait()
                lit, created = LineItemType.get_or_create_for_program(self.program, text='Donation')
                with lock:
                    results.append(lit.id)
            except Exception as e:
                with lock:
                    errors.append(e)
            finally:
                close_old_connections()

        with mock.patch.object(LineItemType, 'save', slow_save):
            threads = [threading.Thread(target=attempt) for _ in range(2)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        self.assertEqual(errors, [])
        self.assertEqual(LineItemType.objects.filter(program=self.program, text='Donation').count(), 1)
        self.assertEqual(len(set(results)), 1)
